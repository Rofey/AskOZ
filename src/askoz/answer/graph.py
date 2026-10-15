"""The request flow as a LangGraph state machine.

    guard ──(identifier found)──────────────────────────────▶ END
      │
    plan ──(out of scope)───────────────────────────────────▶ END
      │
    retrieve ──(nothing found)──────────────────────────────▶ END
      │
    generate ───────────────────────────────────────────────▶ END

Each node reads and updates a shared state dict. Routing decisions are plain
functions on that state, which makes every path easy to test and to trace.
Streaming: `generate` pushes text through LangGraph's custom stream, so
callers see the answer as it's written, whichever path the graph took.

Per-request extras travel in LangGraph's `config`, not in the graph: pass
`config={"configurable": {"on_usage": meter.add}}` to collect the token usage
of every Claude call made for that request.
"""

from typing import Literal, NotRequired, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from askoz.answer.context import SourcePage, group_into_pages, ranked_chunks
from askoz.answer.generate import generate_answer
from askoz.answer.pii import find_identifiers
from askoz.answer.rewrite import QueryPlan, plan_queries
from askoz.retrieval.search import Searcher

OUT_OF_SCOPE = (
    "I can only help with questions about Australian Government services and "
    "obligations, such as tax, super, Medicare and study loans."
)
NOTHING_FOUND = (
    "I couldn't find official information about that in the pages I search. "
    "Try rephrasing, or check australia.gov.au."
)


def _on_usage(config: RunnableConfig):
    return (config.get("configurable") or {}).get("on_usage")


class AskState(TypedDict):
    question: str
    identifiers: NotRequired[list[str]]  # kinds of personal identifier found
    plan: NotRequired[QueryPlan]
    pages: NotRequired[list[SourcePage]]  # retrieved candidates
    answer: NotRequired[str]
    sources: NotRequired[list[SourcePage]]  # pages actually cited
    route: NotRequired[Literal["blocked", "out_of_scope", "nothing_found", "answered", "refused"]]


def build_graph(searcher: Searcher | None = None) -> CompiledStateGraph:
    searcher = searcher or Searcher()

    def guard(state: AskState) -> dict:
        found = find_identifiers(state["question"])
        if not found:
            return {"identifiers": []}
        kinds = " and ".join(found)
        return {
            "identifiers": found,
            "route": "blocked",
            "answer": (
                f"Your question looks like it contains a {kinds}. For your privacy, "
                "I haven't processed it. Please ask again without the number. I never "
                "need personal identifiers to answer general questions."
            ),
        }

    def plan(state: AskState, config: RunnableConfig) -> dict:
        query_plan = plan_queries(state["question"], on_usage=_on_usage(config))
        if not query_plan.in_scope:
            return {"plan": query_plan, "route": "out_of_scope", "answer": OUT_OF_SCOPE}
        return {"plan": query_plan}

    def retrieve(state: AskState) -> dict:
        query_plan = state.get("plan")
        assert query_plan is not None  # set by `plan`, which always runs first
        queries = [state["question"], *query_plan.search_queries]
        pages = group_into_pages(ranked_chunks(searcher, queries))
        if not pages:
            return {"pages": [], "route": "nothing_found", "answer": NOTHING_FOUND}
        return {"pages": pages}

    def generate(state: AskState, config: RunnableConfig) -> dict:
        write = get_stream_writer()
        answer = generate_answer(
            state["question"],
            state.get("pages", []),
            on_text=lambda t: write({"text": t}),
            on_usage=_on_usage(config),
        )
        return {
            "answer": answer.text,
            "sources": answer.sources,
            "route": "refused" if answer.refused else "answered",
        }

    def stop_if_routed(next_node: str):
        return lambda state: END if state.get("route") else next_node

    graph = StateGraph(AskState)
    graph.add_node("guard", guard)
    graph.add_node("plan", plan)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_edge(START, "guard")
    graph.add_conditional_edges("guard", stop_if_routed("plan"), ["plan", END])
    graph.add_conditional_edges("plan", stop_if_routed("retrieve"), ["retrieve", END])
    graph.add_conditional_edges("retrieve", stop_if_routed("generate"), ["generate", END])
    graph.add_edge("generate", END)
    return graph.compile()
