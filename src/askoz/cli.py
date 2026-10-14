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
    args = parser.parse_args()

    if args.command == "doctor":
        sys.exit(doctor())
