#!/usr/bin/env python3
"""Apply pending sql/*.sql migrations (tracked in platform.schema_migration).

Loads configs/.env automatically. For local Linux Docker Postgres:
  scripts/docker/start_linux_docker_stack.sh
  PYTHONPATH=. python scripts/database/apply_sql_migrations.py

Mac thin clients typically use Supabase (SUPABASE_DB_PASSWORD in configs/.env).
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / "configs" / ".env")
load_dotenv(_ROOT / ".env")

from app_skeleton.api.sql_migrations import apply_pending_migrations, db_conn


def main() -> int:
    applied = apply_pending_migrations(conn_str=db_conn())
    if not applied:
        print("No pending migrations.")
        return 0
    print(f"Applied {len(applied)} migration(s):")
    for name in applied:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
