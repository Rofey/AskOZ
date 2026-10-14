"""Command-line entry point: `uv run askoz <command>`."""

import argparse
import sys

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
