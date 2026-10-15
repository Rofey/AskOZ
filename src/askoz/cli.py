"""Command-line entry point: `uv run askoz <command>`."""

import argparse
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import psycopg
import redis

from askoz.config import get_settings
from askoz.logging import configure_logging, get_logger

log = get_logger(__name__)


def doctor() -> int:
    """Check that every service the app depends on is reachable."""
    settings = get_settings()
    healthy = True

    try:
        with psycopg.connect(str(settings.database_url), connect_timeout=3) as conn:
            row = conn.execute(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            ).fetchone()
        if row is None:
            log.error("postgres_missing_pgvector")
            healthy = False
        else:
            log.info("postgres_ok", pgvector=row[0])
    except psycopg.Error as exc:
        log.error("postgres_unreachable", error=str(exc))
        healthy = False

    try:
        redis.Redis.from_url(str(settings.redis_url), socket_connect_timeout=3).ping()
        log.info("redis_ok")
    except redis.RedisError as exc:
        log.error("redis_unreachable", error=str(exc))
        healthy = False

    return 0 if healthy else 1


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(prog="askoz")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check connectivity to Postgres and Redis")
    sub.add_parser("migrate", help="apply pending database migrations")
    sub.add_parser("sources", help="list crawlable sources")
    crawl = sub.add_parser("crawl", help="crawl one source into raw page storage")
    crawl.add_argument("source")
    crawl.add_argument("--limit", type=int, help="stop after storing this many pages")
    ingest = sub.add_parser("ingest", help="clean, chunk and embed crawled pages into pgvector")
    ingest.add_argument("--source", help="only this source (default: all)")
    ingest.add_argument("--limit", type=int, help="only the first N pages")
    ingest.add_argument(
        "--rebuild", action="store_true", help="re-index everything (after changing chunking)"
    )
    search = sub.add_parser("search", help="search the index")
    search.add_argument("question")
    search.add_argument("--mode", default="vector", help="vector | keyword | hybrid | rerank")
    search.add_argument("-k", type=int, default=5, help="number of results")
    search.add_argument(
        "--instruct", action="store_true", help="add bge's query instruction prefix"
    )
    compare = sub.add_parser("compare", help="run one question through every search mode")
    compare.add_argument("question")
    compare.add_argument("-k", type=int, default=5)
    compare.add_argument("--instruct", action="store_true")
    evaluate = sub.add_parser("eval", help="score retrieval against the golden question set")
    evaluate.add_argument("--modes", default="vector,keyword,hybrid,rerank")
    evaluate.add_argument("--instruct", action="store_true")
    evaluate.add_argument("--validate", action="store_true", help="only check the golden set")
    evaluate.add_argument("--save-baseline", action="store_true")
    evaluate.add_argument("--check", action="store_true", help="exit 1 if worse than baseline")
    evaluate.add_argument("--show-misses", action="store_true")
    ask = sub.add_parser("ask", help="answer a question with citations")
    ask.add_argument("question")
    ask.add_argument("-v", "--verbose", action="store_true", help="show the query plan")
    args = parser.parse_args()

    # Imported per command so `askoz doctor` doesn't pay Scrapy's import cost.
    if args.command == "doctor":
        sys.exit(doctor())
    elif args.command == "migrate":
        from askoz.db import migrate

        applied = migrate()
        log.info("migrations_applied", versions=applied or "none pending")
    elif args.command == "sources":
        from askoz.crawl.sources import SOURCES

        for source in SOURCES.values():
            mode = "sitemap" if source.sitemap_url else "links"
            print(f"{source.name:20} {mode:8} {source.domain}")
    elif args.command == "crawl":
        from askoz.crawl.runner import run_crawl
        from askoz.crawl.sources import SOURCES

        if args.source not in SOURCES:
            parser.error(f"unknown source {args.source!r}; choose from {', '.join(SOURCES)}")
        run_crawl(args.source, limit=args.limit)
    elif args.command == "ingest":
        from askoz.ingest.pipeline import ingest

        stats = ingest(source=args.source, limit=args.limit, rebuild=args.rebuild)
        log.info(
            "ingest_done",
            pages=stats.pages,
            skipped_no_content=stats.skipped_no_content,
            chunks_written=stats.chunks_written,
        )
    elif args.command in ("search", "compare"):
        from askoz.retrieval.search import MODES, Mode, Searcher

        if args.command == "search" and args.mode not in MODES:
            parser.error(f"--mode must be one of {', '.join(MODES)}")
        modes: list[Mode] = [args.mode] if args.command == "search" else list(MODES)
        searcher = Searcher(query_instruction=args.instruct)
        for mode in modes:
            print(f"\n=== {mode} ===")
            results = searcher.search(args.question, mode=mode, top_k=args.k)
            for rank, result in enumerate(results, 1):
                meta = result.node.metadata
                section = (meta.get("header_path") or "/").strip("/").split("/")[-1]
                print(f"{rank}. [{result.score or 0:.3f}] {meta['title']} > {section or '(top)'}")
                print(f"   {meta['url']}")
    elif args.command == "eval":
        sys.exit(run_eval(args))
    elif args.command == "ask":
        run_ask(args.question, verbose=args.verbose)


def run_ask(question: str, *, verbose: bool) -> None:
    import anthropic

    from askoz.answer.graph import build_graph

    final: dict[str, Any] = {}
    streamed = False
    stream = build_graph().stream({"question": question}, stream_mode=["custom", "values"])
    try:
        for mode, chunk in cast(Iterator[tuple[str, dict[str, Any]]], stream):
            if mode == "custom":
                print(chunk["text"], end="", flush=True)
                streamed = True
            else:
                final = chunk
    except anthropic.APIStatusError as exc:
        # Short message for the person, full detail (incl. request id) for the logs.
        log.error("claude_api_error", status=exc.status_code, request_id=exc.request_id)
        sys.exit(f"Claude API error {exc.status_code}: {exc.message}")
    except anthropic.APIConnectionError as exc:
        log.error("claude_api_unreachable", error=str(exc))
        sys.exit("Couldn't reach the Claude API. Check your internet connection.")
    if not streamed:
        print(final.get("answer", ""))
    if final.get("sources"):
        print("\n\nSources:")
        for number, page in enumerate(final["sources"], 1):
            print(f"[{number}] {page.title}\n    {page.url}")
    if verbose:
        plan = final.get("plan")
        print(f"\nroute: {final.get('route')}")
        if plan:
            print(f"search queries: {plan.search_queries}")
        print(f"pages retrieved: {[p.title for p in final.get('pages', [])]}")


def run_eval(args: argparse.Namespace) -> int:
    import json
    from datetime import datetime

    from askoz.evals.retrieval import (
        BASELINE_PATH,
        check_against_baseline,
        evaluate,
        load_golden,
        validate,
    )

    golden = load_golden()
    problems = validate(golden)
    for problem in problems:
        print(f"golden set problem: {problem}")
    if problems or args.validate:
        print(f"{len(golden.questions)} questions, {len(problems)} problems")
        return 1 if problems else 0

    report = evaluate(golden, args.modes.split(","), query_instruction=args.instruct)
    styles = sorted({q.style for q in golden.questions})
    print(f"\n{len(golden.questions)} questions | query instruction: {args.instruct}\n")
    print(f"{'mode':8} {'hit@1':>6} {'hit@5':>6} {'hit@10':>6} {'MRR':>6}   hit@5 by style")
    for mode, result in report["modes"].items():
        o = result["overall"]
        by_style = "  ".join(f"{s} {result['by_style'][s]['hit@5']:.2f}" for s in styles)
        print(
            f"{mode:8} {o['hit@1']:6.2f} {o['hit@5']:6.2f} {o['hit@10']:6.2f} {o['mrr']:6.2f}"
            f"   {by_style}"
        )
        if args.show_misses:
            misses = [f"{qid} ({r or '-'})" for qid, r in result["ranks"].items() if not r or r > 5]
            print(f"         not in top 5: {', '.join(misses) or 'none'}")

    out_dir = Path("data/eval")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"retrieval-{datetime.now():%Y%m%d-%H%M%S}.json"
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nreport: {out_file}")

    if args.save_baseline:
        BASELINE_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"baseline saved: {BASELINE_PATH}")
    if args.check:
        regressions = check_against_baseline(report)
        for regression in regressions:
            print(f"REGRESSION {regression}")
        return 1 if regressions else 0
    return 0
