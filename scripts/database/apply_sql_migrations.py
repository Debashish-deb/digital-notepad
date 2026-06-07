#!/usr/bin/env python3
"""Apply pending sql/*.sql migrations (tracked in platform.schema_migration)."""
from __future__ import annotations

import sys

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
