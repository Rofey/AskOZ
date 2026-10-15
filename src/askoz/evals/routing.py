"""Routing eval: coverage decisions and agency referrals from the query planner.

Cheap to run: one planner call per question (fractions of a cent on Haiku).
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from askoz.answer.rewrite import plan_queries
from askoz.config import get_settings

ROUTING_PATH = Path(__file__).resolve().parents[3] / "eval" / "routing.yaml"

Expected = Literal["covered", "partly", "not_covered", "out_of_scope"]


class RoutingCase(BaseModel):
    question: str
    expect: Expected
    refer_to: list[str] = []
    covered_by: str | None = None  # once this source is live, expect "covered"

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
        plan = plan_queries(case.question)
        expect, refer_to = case.expected_now()
        got: Expected = "out_of_scope" if not plan.in_scope else plan.coverage
        coverage_ok = got == expect
        agency_ok = not refer_to or plan.refer_to in refer_to
        results.append(
            {
                "question": case.question,
                "expect": expect,
                "got": got,
                "refer_to": plan.refer_to,
                "ok": coverage_ok and agency_ok,
                "suggestion": plan.related_question,
            }
        )
    return results
