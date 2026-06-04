#!/usr/bin/env python3
"""Daily ingestion: read-only storage scans, optional Supabase sync, lightweight thumbnails.

Safe by design: no delete, no move, no WebDAV writes except optional preview JPEG cache locally.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "configs" / ".env")
load_dotenv(ROOT / "deploy" / "university-desktop" / ".env")
load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
LOGGER = logging.getLogger("scheduled_ingest")


def _datacloud_scan(max_entries: int) -> dict:
    from app_skeleton.storage import datacloud_webdav

    if not datacloud_webdav.is_configured():
        return {"status": "skipped", "provider": "datacloud_webdav", "reason": "not_configured"}
    try:
        manifest = datacloud_webdav.build_manifest("", max_entries=max_entries)
        return {
            "status": "ok",
            "provider": "datacloud_webdav",
            "entry_count": len(manifest.get("entries") or []),
        }
    except Exception as exc:
        LOGGER.exception("DataCloud scan failed")
        return {"status": "error", "provider": "datacloud_webdav", "detail": str(exc)}


def _pdrive_scan(max_entries: int) -> dict:
    from app_skeleton.storage import pdrive_smb
    from app_skeleton.storage.env import pdrive_enabled

    if not pdrive_enabled():
        return {"status": "skipped", "provider": "pdrive_smb", "reason": "disabled"}
    try:
        manifest = pdrive_smb.build_manifest("", max_entries=max_entries)
        return {
            "status": "ok",
            "provider": "pdrive_smb",
            "entry_count": len(manifest.get("entries") or []),
        }
    except Exception as exc:
        LOGGER.exception("P-drive scan failed")
        return {"status": "error", "provider": "pdrive_smb", "detail": str(exc)}


def _supabase_sync(dry_run: bool) -> dict:
    from app_skeleton.api.supabase_sync import (
        supabase_hosted_password_set,
        supabase_sync_enabled,
        sync_documents_to_supabase,
    )

    if not supabase_sync_enabled():
        return {"status": "skipped", "step": "supabase_sync", "reason": "SUPABASE_SYNC_ENABLED=false"}
    if not supabase_hosted_password_set():
        return {
            "status": "skipped",
            "step": "supabase_sync",
            "reason": "SUPABASE_DB_PASSWORD unset",
        }
    try:
        return sync_documents_to_supabase(dry_run=dry_run)
    except Exception as exc:
        LOGGER.exception("Supabase sync failed")
        return {"status": "error", "step": "supabase_sync", "detail": str(exc)}


def _thumbnails() -> dict:
    from app_skeleton.api.thumbnail_service import scan_and_thumbnail_directory
    from app_skeleton.storage.env import pdrive_mount_path

    roots: list[Path] = []
    lab = os.getenv("LAB_STORAGE_ROOT", "").strip()
    if lab:
        roots.append(Path(lab))
    mount = pdrive_mount_path()
    if mount:
        roots.append(Path(mount))
    if not roots:
        return {"status": "skipped", "step": "thumbnails", "reason": "no_local_root"}

    results = []
    for root in roots:
        results.append(scan_and_thumbnail_directory(root))
    return {"status": "ok", "step": "thumbnails", "roots": results}


def run(
    *,
    max_entries: int = 500,
    skip_supabase: bool = False,
    skip_thumbnails: bool = False,
    supabase_dry_run: bool = False,
) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    report = {
        "started_at": started,
        "datacloud": _datacloud_scan(max_entries),
        "pdrive": _pdrive_scan(max_entries),
    }
    if not skip_supabase:
        report["supabase"] = _supabase_sync(supabase_dry_run)
    if not skip_thumbnails:
        report["thumbnails"] = _thumbnails()
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Scheduled read-only ingestion (desktop)")
    parser.add_argument("--max-entries", type=int, default=500)
    parser.add_argument("--skip-supabase", action="store_true")
    parser.add_argument("--skip-thumbnails", action="store_true")
    parser.add_argument("--supabase-dry-run", action="store_true")
    args = parser.parse_args()

    result = run(
        max_entries=args.max_entries,
        skip_supabase=args.skip_supabase,
        skip_thumbnails=args.skip_thumbnails,
        supabase_dry_run=args.supabase_dry_run,
    )
    print(json.dumps(result, indent=2))
    errors = [
        step
        for step in ("datacloud", "pdrive", "supabase")
        if (result.get(step) or {}).get("status") == "error"
    ]
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
