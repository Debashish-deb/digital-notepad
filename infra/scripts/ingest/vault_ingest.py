#!/usr/bin/env python3
"""CLI for Raw Knowledge Vault ingestion (resumable scan, per-project, retry-failed)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from omeia.api.paths import DATABASE_ROOT  # noqa: E402
from omeia.api.vault_ingestion_engine import (  # noqa: E402
    ingest_project,
    retry_failed_extractions,
    run_ingest_scan,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Raw Knowledge Vault ingestion")
    parser.add_argument("--full", action="store_true", help="Scan full DATABASE_ROOT")
    parser.add_argument("--project", type=str, default=None, help="Ingest one project folder by name")
    parser.add_argument("--retry-failed", action="store_true", help="Re-process failed extraction rows only")
    parser.add_argument("--resume", action="store_true", help="Resume from vault_scan_checkpoint")
    parser.add_argument("--limit", type=int, default=500, help="Max files (full scan) or retry batch size")
    args = parser.parse_args()

    if args.retry_failed:
        result = retry_failed_extractions(
            project_hint=args.project,
            limit=args.limit,
        )
    elif args.project:
        result = ingest_project(args.project, resume=args.resume)
    elif args.full:
        result = run_ingest_scan(scan_root=DATABASE_ROOT, resume=args.resume, max_files=args.limit)
    else:
        parser.error("Specify --full, --project NAME, or --retry-failed")
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
