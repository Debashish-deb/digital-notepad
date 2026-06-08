#!/usr/bin/env python3
"""Delete non-canonical duplicate copies from disk and inventory (dry-run by default)."""
from __future__ import annotations

import argparse
import ast
import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
ROOT = _SCRIPT.parents[2]
sys.path.insert(0, str(ROOT))

from omeia.api.document_library_service import (  # noqa: E402
    AUDIT_INVENTORY_JSON,
    INVENTORY_JSON,
    invalidate_cache,
)
from omeia.api.paths import DATABASE_ROOT  # noqa: E402

LOGGER = logging.getLogger(__name__)
LOG_DIR = ROOT / "reports" / "document_library_audit" / "metadata_v2"
REVIEW_CSV = LOG_DIR / "duplicate_review_queue.csv"
DELETION_LOG = LOG_DIR / "duplicate_deletion_log.csv"


def _review_asset_ids() -> set[str]:
    if not REVIEW_CSV.is_file():
        return set()
    ids: set[str] = set()
    with REVIEW_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            aid = (row.get("asset_id") or "").strip()
            if aid:
                ids.add(aid)
    return ids


def _load_inventory() -> list[dict]:
    data = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _save_inventory(rows: list[dict]) -> None:
    INVENTORY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    AUDIT_INVENTORY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def delete_duplicates(
    *,
    dry_run: bool = True,
    include_review_queue: bool = False,
) -> dict:
    review_ids = _review_asset_ids()
    rows = _load_inventory()
    by_id = {r["asset_id"]: r for r in rows if r.get("asset_id")}

    candidates = [
        r for r in rows
        if r.get("duplicate_status") == "duplicate"
        and r.get("canonical_asset_id")
        and by_id.get(r["canonical_asset_id"])
    ]

    stats = {
        "dry_run": dry_run,
        "candidates": len(candidates),
        "deleted_disk": 0,
        "removed_inventory": 0,
        "skipped_review_queue": 0,
        "skipped_missing_canonical": 0,
        "disk_missing": 0,
        "errors": 0,
    }
    log_rows: list[dict] = []

    remove_ids: set[str] = set()

    for row in candidates:
        aid = row["asset_id"]
        if aid in review_ids and not include_review_queue:
            stats["skipped_review_queue"] += 1
            log_rows.append({
                "asset_id": aid,
                "action": "skipped_review_queue",
                "logical_path": row.get("logical_path"),
                "canonical_asset_id": row.get("canonical_asset_id"),
            })
            continue

        canonical = by_id.get(row["canonical_asset_id"])
        if not canonical:
            stats["skipped_missing_canonical"] += 1
            continue

        logical = row.get("logical_path") or ""
        disk_path = DATABASE_ROOT / logical

        action = "deleted" if not dry_run else "would_delete"
        if disk_path.is_file():
            if not dry_run:
                try:
                    disk_path.unlink()
                    stats["deleted_disk"] += 1
                except OSError as exc:
                    stats["errors"] += 1
                    action = f"disk_error:{exc}"
                    log_rows.append({
                        "asset_id": aid,
                        "action": action,
                        "logical_path": logical,
                        "canonical_asset_id": row.get("canonical_asset_id"),
                    })
                    continue
            else:
                stats["deleted_disk"] += 1
        else:
            stats["disk_missing"] += 1
            action = "disk_already_missing"

        remove_ids.add(aid)
        stats["removed_inventory"] += 1
        log_rows.append({
            "asset_id": aid,
            "action": action,
            "logical_path": logical,
            "canonical_asset_id": row.get("canonical_asset_id"),
            "canonical_path": canonical.get("logical_path"),
        })

    if not dry_run and remove_ids:
        kept = [r for r in rows if r.get("asset_id") not in remove_ids]
        # Re-mark canonical rows that were in duplicate groups
        for r in kept:
            if r.get("duplicate_status") == "canonical":
                siblings_left = sum(
                    1 for x in kept
                    if x.get("checksum_sha256") == r.get("checksum_sha256")
                    and x.get("asset_id") != r.get("asset_id")
                )
                if siblings_left == 0:
                    r["duplicate_status"] = "unique"
                    r["inventory_active"] = True
        _save_inventory(kept)
        invalidate_cache()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with DELETION_LOG.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["asset_id", "action", "logical_path", "canonical_asset_id", "canonical_path"],
            extrasaction="ignore",
        )
        w.writeheader()
        w.writerows(log_rows)

    stats["deletion_log"] = str(DELETION_LOG)
    stats["timestamp"] = datetime.now(timezone.utc).isoformat()
    stats["remaining_inventory"] = len(rows) - len(remove_ids) if not dry_run else len(rows)
    return stats


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Actually delete files (default: dry-run)")
    parser.add_argument(
        "--include-review-queue",
        action="store_true",
        help="Also delete 59 duplicates flagged for human review (version variants)",
    )
    args = parser.parse_args()
    stats = delete_duplicates(
        dry_run=not args.execute,
        include_review_queue=args.include_review_queue,
    )
    print(json.dumps(stats, indent=2))
    if stats["dry_run"]:
        print("\nDry-run only. Re-run with --execute to delete files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
