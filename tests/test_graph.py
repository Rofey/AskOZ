"""Routing tests for the answer graph, with the LLM and search stubbed out."""

from typing import Any

import pytest

import askoz.answer.graph as graph_module
from askoz.answer.context import SourcePage
from askoz.answer.generate import Answer
from askoz.answer.rewrite import QueryPlan
from askoz.retrieval.search import Searcher

PAGE = SourcePage(url="https://www.ato.gov.au/x", title="X", last_updated=None, sections=["s"])


def _run(question: str) -> dict[str, Any]:
    graph = graph_module.build_graph(searcher=Searcher.__new__(Searcher))  # never queried
    return graph.invoke({"question": question})


@pytest.fixture
def stubs(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    calls: dict[str, list[str]] = {"plan": [], "generate": []}

    def plan(question: str, on_usage: Any = None) -> QueryPlan:
        calls["plan"].append(question)
        return QueryPlan(in_scope="recipe" not in question, search_queries=["official terms"])

    def generate(
        question: str, pages: list[SourcePage], on_text: Any = None, on_usage: Any = None
    ) -> Answer:
        calls["generate"].append(question)
        return Answer(text="answer [1]", sources=pages)

    monkeypatch.setattr(graph_module, "plan_queries", plan)
    monkeypatch.setattr(graph_module, "generate_answer", generate)
    monkeypatch.setattr(graph_module, "ranked_chunks", lambda searcher, queries: [])
    monkeypatch.setattr(graph_module, "group_into_pages", lambda chunks: [PAGE])
    return calls


def test_identifier_stops_before_any_llm_call(stubs: dict[str, list[str]]) -> None:
    state = _run("my tfn is 123 456 782, where is my refund")
    assert state["route"] == "blocked"
    assert stubs["plan"] == [] and stubs["generate"] == []


def test_out_of_scope_skips_retrieval_and_generation(stubs: dict[str, list[str]]) -> None:
    state = _run("give me a pasta recipe")
    assert state["route"] == "out_of_scope"
    assert stubs["generate"] == []


def test_normal_question_is_answered_with_sources(stubs: dict[str, list[str]]) -> None:
    state = _run("how much tax do backpackers pay")
    assert state["route"] == "answered"
    assert state["sources"] == [PAGE]
