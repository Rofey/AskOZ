"""Routing tests for the answer graph, with the LLM and search stubbed out."""

from typing import Any, get_args

import pytest

import askoz.answer.graph as graph_module
from askoz.answer.agencies import AGENCIES, AgencyId
from askoz.answer.context import SourcePage
from askoz.answer.generate import Answer
from askoz.answer.rewrite import QueryPlan
from askoz.retrieval.search import Searcher

PAGE = SourcePage(url="https://www.ato.gov.au/x", title="X", last_updated=None, sections=["s"])

# What the stub planner returns, keyed by a word in the question.
PLANS = {
    "recipe": QueryPlan(in_scope=False, search_queries=["q"]),
    "visa": QueryPlan(
        in_scope=True,
        coverage="not_covered",
        refer_to="home_affairs",
        search_queries=["q"],
        tax_angle_question="Do I need a TFN to work?",
    ),
    "pension": QueryPlan(
        in_scope=True, coverage="partly", refer_to="services_australia", search_queries=["q"]
    ),
}


def _run(question: str) -> dict[str, Any]:
    graph = graph_module.build_graph(searcher=Searcher.__new__(Searcher))  # never queried
    return graph.invoke({"question": question})


@pytest.fixture
def stubs(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    calls: dict[str, list[Any]] = {"plan": [], "generate": []}

    def plan(question: str, on_usage: Any = None) -> QueryPlan:
        calls["plan"].append(question)
        for word, query_plan in PLANS.items():
            if word in question:
                return query_plan
        return QueryPlan(in_scope=True, coverage="covered", search_queries=["official terms"])

    def generate(
        question: str,
        pages: list[SourcePage],
        on_text: Any = None,
        on_usage: Any = None,
        referred_elsewhere: Any = None,
    ) -> Answer:
        calls["generate"].append(referred_elsewhere)
        return Answer(text="answer [1]", sources=pages)

    monkeypatch.setattr(graph_module, "plan_queries", plan)
    monkeypatch.setattr(graph_module, "generate_answer", generate)
    monkeypatch.setattr(graph_module, "ranked_chunks", lambda searcher, queries: [])
    monkeypatch.setattr(graph_module, "group_into_pages", lambda chunks: [PAGE])
    return calls


def test_identifier_stops_before_any_llm_call(stubs: dict[str, list[Any]]) -> None:
    state = _run("my tfn is 123 456 782, where is my refund")
    assert state["route"] == "blocked"
    assert stubs["plan"] == [] and stubs["generate"] == []


def test_out_of_scope_skips_retrieval_and_generation(stubs: dict[str, list[Any]]) -> None:
    state = _run("give me a pasta recipe")
    assert state["route"] == "out_of_scope"
    assert stubs["generate"] == []


def test_normal_question_is_answered_with_sources(stubs: dict[str, list[Any]]) -> None:
    state = _run("how much tax do backpackers pay")
    assert state["route"] == "answered"
    assert state["sources"] == [PAGE]
    assert "referral" not in state


def test_other_agencys_topic_gets_template_referral_without_answer_call(
    stubs: dict[str, list[Any]],
) -> None:
    state = _run("how do I apply for a partner visa")
    assert state["route"] == "referral"
    assert stubs["generate"] == []  # no expensive answer call
    assert state["referral"] is AGENCIES["home_affairs"]
    assert "can't answer this one yet" in state["answer"]
    assert state["suggestion"] == "Do I need a TFN to work?"


def test_partly_covered_answers_ato_part_and_refers_the_rest(stubs: dict[str, list[Any]]) -> None:
    state = _run("how much is the age pension and is it taxed")
    assert state["route"] == "answered"
    assert stubs["generate"] == [AGENCIES["services_australia"]]
    assert state["referral"] is AGENCIES["services_australia"]


def test_agency_directory_is_complete_and_safe() -> None:
    assert set(AGENCIES) == set(get_args(AgencyId))  # the planner's choices match the directory
    for agency in AGENCIES.values():
        assert agency.links
        assert all(link.url.startswith("https://") for link in agency.links)
