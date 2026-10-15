"""Routing eval: coverage decisions and agency referrals from the query planner.

Cheap to run: one planner call per question (fractions of a cent on Haiku).
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from askoz.answer.rewrite import plan_queries

ROUTING_PATH = Path(__file__).resolve().parents[3] / "eval" / "routing.yaml"

Expected = Literal["covered", "partly", "not_covered", "out_of_scope"]


class RoutingCase(BaseModel):
    question: str
    expect: Expected
    refer_to: list[str] = []


def load_cases(path: Path = ROUTING_PATH) -> list[RoutingCase]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [RoutingCase.model_validate(q) for q in data["questions"]]


def run_routing_eval(cases: list[RoutingCase]) -> list[dict]:
    results = []
    for case in cases:
        plan = plan_queries(case.question)
        got: Expected = "out_of_scope" if not plan.in_scope else plan.coverage
        coverage_ok = got == case.expect
        agency_ok = not case.refer_to or plan.refer_to in case.refer_to
        results.append(
            {
                "question": case.question,
                "expect": case.expect,
                "got": got,
                "refer_to": plan.refer_to,
                "ok": coverage_ok and agency_ok,
                "suggestion": plan.tax_angle_question,
            }
        )
    return results
