"""Track and apply sql/*.sql migrations idempotently."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import psycopg

LOGGER = logging.getLogger(__name__)

BLUEPRINT_ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = BLUEPRINT_ROOT / "sql"


def db_conn() -> str:
    from omeia.api.supabase_config import postgres_conn

    return postgres_conn()


def ensure_migration_table(cur) -> None:
    cur.execute("CREATE SCHEMA IF NOT EXISTS platform;")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS platform.schema_migration (
          filename text PRIMARY KEY,
          applied_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )


def pending_sql_files() -> list[Path]:
    return sorted(SQL_DIR.glob("*.sql"))


def apply_pending_migrations(*, conn_str: str | None = None) -> list[str]:
    """Apply any sql/*.sql not yet recorded. Returns filenames applied."""
    conn_str = conn_str or db_conn()
    files = pending_sql_files()
    if not files:
        return []

    applied: list[str] = []
    with psycopg.connect(conn_str, connect_timeout=30) as conn:
        with conn.cursor() as cur:
            ensure_migration_table(cur)
            cur.execute("SELECT filename FROM platform.schema_migration;")
            done = {row[0] for row in cur.fetchall()}
            if not done:
                cur.execute("SELECT to_regclass('platform.raw_asset_vault');")
                if cur.fetchone()[0]:
                    LOGGER.info(
                        "Bootstrapping schema_migration for existing database (skip re-applying legacy SQL)."
                    )
                    for path in files:
                        cur.execute(
                            """
                            INSERT INTO platform.schema_migration (filename)
                            VALUES (%s) ON CONFLICT (filename) DO NOTHING;
                            """,
                            (path.name,),
                        )
                    cur.execute("SELECT filename FROM platform.schema_migration;")
                    done = {row[0] for row in cur.fetchall()}
            for path in files:
                name = path.name
                if name in done:
                    continue
                LOGGER.info("Applying migration %s", name)
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO platform.schema_migration (filename) VALUES (%s);",
                    (name,),
                )
                applied.append(name)
        conn.commit()
    return applied
