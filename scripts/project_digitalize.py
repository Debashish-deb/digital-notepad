#!/usr/bin/env python3
"""CLI: project folder digitalization (LAB_STORAGE_ROOT or PROJECTS_ROOT)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BLUEPRINT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BLUEPRINT))

from dotenv import load_dotenv

load_dotenv(BLUEPRINT / "configs" / ".env")
load_dotenv()

from app_skeleton.api.project_digitalization_engine import run_digitalization
from app_skeleton.api.vault_ingestion_engine import retry_failed_extractions


def main() -> int:
    p = argparse.ArgumentParser(description="Digitalize project folders into Raw Knowledge Vault")
    p.add_argument("--full", action="store_true", help="Scan all top-level project folders")
    p.add_argument("--project", metavar="NAME", help="Single project folder name")
    p.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    p.add_argument("--dry-run", action="store_true", help="Count files only; no DB writes")
    p.add_argument("--retry-failed", action="store_true", help="Re-extract failed vault rows")
    p.add_argument("--max-files", type=int, default=None)
    args = p.parse_args()

    if args.retry_failed:
        report = retry_failed_extractions(project_hint=args.project, limit=args.max_files or 500)
        print(report)
        return 0

    mode = "project" if args.project else "full"
    report = run_digitalization(
        mode=mode,
        project_name=args.project,
        resume=args.resume,
        dry_run=args.dry_run,
        max_files=args.max_files,
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
