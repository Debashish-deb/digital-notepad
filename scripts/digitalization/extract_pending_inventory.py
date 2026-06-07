#!/usr/bin/env python3
"""Extract text/metadata for inventory files pending digitalization."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
ROOT = _SCRIPT.parents[2]
sys.path.insert(0, str(ROOT))

from app_skeleton.api import document_extraction as de  # noqa: E402
from app_skeleton.api.document_library_service import (  # noqa: E402
    AUDIT_INVENTORY_JSON,
    INVENTORY_JSON,
    _row_has_extracted_text,
    invalidate_cache,
    reconcile_vector_status,
)
from app_skeleton.api.paths import DATABASE_ROOT  # noqa: E402

LOGGER = logging.getLogger(__name__)


def _load_inventory() -> list[dict]:
    for path in (INVENTORY_JSON, AUDIT_INVENTORY_JSON):
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
    raise FileNotFoundError("No inventory JSON found")


def _save_inventory(rows: list[dict]) -> None:
    INVENTORY_JSON.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    if AUDIT_INVENTORY_JSON.is_file():
        AUDIT_INVENTORY_JSON.write_text(
            json.dumps(rows, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _needs_extraction(row: dict) -> bool:
    ext = (row.get("extraction_status") or "").strip()
    if ext in ("not_started", "failed", "eligible_text"):
        return not _row_has_extracted_text(row)
    return False


def _needs_empty_retry(row: dict) -> bool:
    ext = (row.get("extraction_status") or "").strip()
    return ext == "empty" and not _row_has_extracted_text(row)


def _apply_extraction(row: dict, disk_path: Path) -> tuple[str, dict]:
    result = de.extract_for_vault(disk_path, DATABASE_ROOT)
    status = de.vault_extraction_status(result)
    metadata_json = {
        "extractor": result.extractor,
        "document_kind": result.document_kind,
        "char_count": result.char_count,
        "word_count": result.word_count,
        "warnings": result.warnings[:20],
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        **result.metadata,
    }
    if result.excerpt:
        metadata_json["excerpt"] = result.excerpt[:4000]
    if result.errors:
        metadata_json["error"] = "; ".join(result.errors)[:2000]
    return status, metadata_json


def extract_pending(
    *,
    limit: int | None = None,
    dry_run: bool = False,
    all_unextracted: bool = False,
    retry_empty: bool = False,
) -> dict:
    rows = _load_inventory()
    if retry_empty:
        pending = [r for r in rows if _needs_empty_retry(r)]
    elif all_unextracted:
        pending = [r for r in rows if _needs_extraction(r)]
    else:
        pending = [r for r in rows if (r.get("extraction_status") or "") == "not_started"]
    if limit:
        pending = pending[:limit]

    stats = {
        "mode": "retry_empty" if retry_empty else ("all_unextracted" if all_unextracted else "not_started"),
        "total_pending": len(pending),
        "extracted": 0,
        "metadata_only": 0,
        "failed": 0,
        "skipped": 0,
        "missing_file": 0,
    }

    by_id = {r["asset_id"]: r for r in rows if r.get("asset_id")}

    for row in pending:
        logical = row.get("logical_path") or ""
        disk_path = DATABASE_ROOT / logical
        if not disk_path.is_file():
            stats["missing_file"] += 1
            continue
        if dry_run:
            stats["extracted"] += 1
            continue

        try:
            status, metadata_json = _apply_extraction(row, disk_path)
            target = by_id.get(row["asset_id"], row)
            target["extraction_status"] = status
            target["metadata_json"] = metadata_json
            target["vector_status"] = reconcile_vector_status(target)
            if status == "extracted":
                stats["extracted"] += 1
            elif status == "metadata_only":
                stats["metadata_only"] += 1
            elif status == "empty":
                stats.setdefault("empty", 0)
                stats["empty"] += 1
            elif status in ("failed", "skipped"):
                stats[status if status in stats else "failed"] += 1
            else:
                stats["extracted"] += 1
        except Exception as exc:
            LOGGER.exception("Failed %s: %s", logical, exc)
            target = by_id.get(row["asset_id"], row)
            target["extraction_status"] = "failed"
            target["metadata_json"] = {"error": str(exc)[:500]}
            target["vector_status"] = "not_evaluated"
            stats["failed"] += 1

    if not dry_run:
        _save_inventory(rows)
        invalidate_cache()

    stats["inventory_path"] = str(INVENTORY_JSON)
    return stats


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--all-unextracted",
        action="store_true",
        help="Extract eligible_text/failed/not_started rows missing metadata_json text",
    )
    parser.add_argument(
        "--retry-empty",
        action="store_true",
        help="Re-extract rows marked empty with no stored excerpt",
    )
    args = parser.parse_args()
    stats = extract_pending(
        limit=args.limit,
        dry_run=args.dry_run,
        all_unextracted=args.all_unextracted,
        retry_empty=args.retry_empty,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
