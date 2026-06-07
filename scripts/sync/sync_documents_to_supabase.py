#!/usr/bin/env python3
"""CLI: sync document metadata + truncated text from local Postgres to hosted Supabase."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "configs" / ".env")
load_dotenv()

from app_skeleton.api.supabase_sync import (  # noqa: E402
    sync_documents_to_supabase,
    supabase_hosted_password_set,
    supabase_sync_enabled,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync documents to hosted Supabase Postgres")
    parser.add_argument("--dry-run", action="store_true", help="Count eligible rows without writing")
    parser.add_argument("--limit", type=int, default=None, help="Max local vault rows to consider")
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="ISO timestamp — only rows with vault.updated_at >= since",
    )
    args = parser.parse_args()

    if not args.dry_run and not supabase_sync_enabled():
        print(
            json.dumps(
                {
                    "status": "disabled",
                    "hint": "Set SUPABASE_SYNC_ENABLED=true in configs/.env",
                },
                indent=2,
            )
        )
        return 2

    if not supabase_hosted_password_set():
        print(
            json.dumps(
                {
                    "status": "needs_user_decision",
                    "hint": "Set SUPABASE_DB_PASSWORD in configs/.env before syncing",
                },
                indent=2,
            )
        )
        return 2

    result = sync_documents_to_supabase(
        dry_run=args.dry_run,
        limit=args.limit,
        since=args.since,
    )
    print(json.dumps(result, indent=2))
    if result.get("status") in ("error", "needs_user_decision", "disabled"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
