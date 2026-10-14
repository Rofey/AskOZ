"""Database connection and schema migrations.

Migrations are plain numbered SQL files in db/migrations. Each runs once, in
order, and is recorded in `schema_migrations`. They're applied in a single
transaction under an advisory lock, so two app instances deploying at the
same moment can't both run them, and a failing migration leaves nothing
half-applied.
"""

from pathlib import Path

import psycopg

from askoz.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"
_MIGRATION_LOCK_ID = 7_270_101  # arbitrary, app-wide constant


def connect(*, autocommit: bool = False) -> psycopg.Connection:
    return psycopg.connect(str(get_settings().database_url), autocommit=autocommit)


def migrate() -> list[str]:
    """Apply pending migrations; return the versions applied in this run."""
    applied: list[str] = []
    with connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version text PRIMARY KEY,"
            " applied_at timestamptz NOT NULL DEFAULT now())"
        )
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_ID,))
        done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.stem in done:
                continue
            conn.execute(path.read_bytes())
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
            applied.append(path.stem)
    return applied
