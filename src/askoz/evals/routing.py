"""Routing eval: coverage decisions, agency referrals, ambiguity and follow-ups.

Cheap to run: one planner call per question (fractions of a cent on Haiku).
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from askoz.answer.rewrite import plan_queries
from askoz.config import get_settings

ROUTING_PATH = Path(__file__).resolve().parents[3] / "eval" / "routing.yaml"

Expected = Literal["covered", "partly", "not_covered", "out_of_scope", "clarify"]


class RoutingCase(BaseModel):
    question: str
    expect: Expected
    refer_to: list[str] = []
    covered_by: str | None = None  # once this source is live, expect "covered"
    history: list[str] = []  # earlier questions in the conversation
    # For follow-ups: the standalone rewrite must mention one of these words,
    # i.e. the history was actually used to resolve the question.
    standalone_mentions: list[str] = []

    def expected_now(self) -> tuple[Expected, list[str]]:
        if self.covered_by and self.covered_by in get_settings().live_sources:
            return "covered", []
        return self.expect, self.refer_to


def load_cases(path: Path = ROUTING_PATH) -> list[RoutingCase]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [RoutingCase.model_validate(q) for q in data["questions"]]


def run_routing_eval(cases: list[RoutingCase]) -> list[dict]:
    results = []
    for case in cases:
        plan = plan_queries(case.question, history=case.history)
        expect, refer_to = case.expected_now()
        got: Expected
        if not plan.in_scope:
            got = "out_of_scope"
        elif plan.ambiguous:
            got = "clarify"
        else:
            got = plan.coverage
        agency_ok = expect == "clarify" or not refer_to or plan.refer_to in refer_to
        resolved_ok = not case.standalone_mentions or any(
            word.lower() in plan.standalone_question.lower() for word in case.standalone_mentions
        )
        results.append(
            {
                "question": case.question,
                "history": case.history,
                "expect": expect,
                "got": got,
                "refer_to": plan.refer_to,
                "ok": got == expect and agency_ok and resolved_ok,
                "suggestion": plan.related_question,
                "standalone": plan.standalone_question,
                "options": plan.interpretations,
            }
        )
    return results
