"""Retrieval evaluation against the golden question set.

Metrics are page-level: several chunks from one page count as one result,
because the user is shown pages (as citations), not chunks.

    hit@k  share of questions with at least one relevant page in the top k.
           hit@5 is the headline number: the answer generator in Phase 6 sees
           about five pages, so a miss here usually means a wrong answer.
    MRR    mean reciprocal rank: 1/rank of the first relevant page (0 if not
           in the top 10), averaged. Rewards putting the answer *first*.
"""

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from askoz.db import connect
from askoz.retrieval.search import Mode, Searcher

GOLDEN_PATH = Path(__file__).resolve().parents[3] / "eval" / "golden.yaml"
BASELINE_PATH = GOLDEN_PATH.with_name("baseline.json")
MAX_RANK = 10  # pages considered per question
CHUNKS_FETCHED = 40  # enough chunks to fill MAX_RANK distinct pages
HEADLINE = "hit@5"


class GoldenQuestion(BaseModel):
    id: str
    question: str
    style: Literal["plain", "official", "acronym"]
    relevant: list[str]
    evidence: str


class GoldenSet(BaseModel):
    base_url: str
    questions: list[GoldenQuestion]

    def relevant_urls(self, q: GoldenQuestion) -> set[str]:
        return {self.base_url + path for path in q.relevant}


def load_golden(path: Path = GOLDEN_PATH) -> GoldenSet:
    return GoldenSet.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def validate(golden: GoldenSet) -> list[str]:
    """Return problems with the golden set itself: unknown pages or missing evidence."""
    problems: list[str] = []
    ids = [q.id for q in golden.questions]
    problems += [f"duplicate id: {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    with connect() as conn:
        for q in golden.questions:
            urls = sorted(golden.relevant_urls(q))
            rows = conn.execute(
                "SELECT metadata_->>'url', bool_or(text ILIKE %s) FROM data_chunks"
                " WHERE metadata_->>'url' = ANY(%s) GROUP BY 1",
                (f"%{q.evidence}%", urls),
            ).fetchall()
            found = {url for url, _ in rows}
            problems += [f"{q.id}: page not in index: {u}" for u in urls if u not in found]
            if found and not any(has_evidence for _, has_evidence in rows):
                problems.append(f"{q.id}: evidence {q.evidence!r} not on any relevant page")
    return problems


# Search modes, plus "rewrite": the Phase 6 query planner followed by multi-query
# vector search, i.e. exactly what `askoz ask` retrieves. It calls Claude once per
# question, so it costs money: about $0.01 per question at low effort on Opus.
EvalMode = Mode | Literal["rewrite"]


PLAN_CACHE = Path("data/eval/plan_cache.json")


def cached_plan(question: str) -> list[str]:
    """The rewriter's queries for a question, cached per rewrite model.

    The rewriter is an LLM, so it phrases things a little differently each run.
    Caching makes retrieval experiments compare like with like (and free after
    the first run). Delete the cache to evaluate a new rewrite prompt or model.
    """
    from askoz.answer.rewrite import plan_queries
    from askoz.config import get_settings

    cache = json.loads(PLAN_CACHE.read_text(encoding="utf-8")) if PLAN_CACHE.exists() else {}
    key = f"{get_settings().rewrite_model}|{question}"
    if key not in cache:
        cache[key] = plan_queries(question).search_queries
        PLAN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        PLAN_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return cache[key]


def ranked_pages(searcher: Searcher, question: str, mode: EvalMode) -> list[str]:
    if mode == "rewrite":
        from askoz.answer.context import group_into_pages, ranked_chunks

        queries = [question, *cached_plan(question)]
        return [
            p.url for p in group_into_pages(ranked_chunks(searcher, queries), max_pages=MAX_RANK)
        ]

    pages: list[str] = []
    for result in searcher.search(question, mode=mode, top_k=CHUNKS_FETCHED):
        url = result.node.metadata["url"]
        if url not in pages:
            pages.append(url)
    return pages[:MAX_RANK]


def first_relevant_rank(pages: list[str], relevant: set[str]) -> int | None:
    return next((i for i, url in enumerate(pages, 1) if url in relevant), None)


def metrics(ranks: list[int | None]) -> dict[str, float]:
    n = len(ranks) or 1
    return {
        "hit@1": sum(r is not None and r <= 1 for r in ranks) / n,
        "hit@5": sum(r is not None and r <= 5 for r in ranks) / n,
        "hit@10": sum(r is not None for r in ranks) / n,
        "mrr": sum(1 / r for r in ranks if r is not None) / n,
    }


def evaluate(golden: GoldenSet, modes: list[EvalMode], *, query_instruction: bool = False) -> dict:
    searcher = Searcher(query_instruction=query_instruction)
    report: dict = {
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "query_instruction": query_instruction,
        "questions": len(golden.questions),
        "modes": {},
    }
    for mode in modes:
        per_question = {}
        by_style: dict[str, list[int | None]] = defaultdict(list)
        for q in golden.questions:
            rank = first_relevant_rank(
                ranked_pages(searcher, q.question, mode), golden.relevant_urls(q)
            )
            per_question[q.id] = rank
            by_style[q.style].append(rank)
        report["modes"][mode] = {
            "overall": metrics(list(per_question.values())),
            "by_style": {style: metrics(r) for style, r in sorted(by_style.items())},
            "ranks": per_question,
        }
    return report


def check_against_baseline(report: dict, *, tolerance: float = 0.02) -> list[str]:
    """Regressions of the headline metric versus the committed baseline."""
    if not BASELINE_PATH.exists():
        return ["no baseline yet: run `askoz eval --save-baseline`"]
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    regressions = []
    for mode, result in report["modes"].items():
        before = baseline["modes"].get(mode, {}).get("overall", {}).get(HEADLINE)
        after = result["overall"][HEADLINE]
        if before is not None and after < before - tolerance:
            regressions.append(f"{mode}: {HEADLINE} fell from {before:.2f} to {after:.2f}")
    return regressions
