#!/usr/bin/env python3
"""Reconcile extraction/vector/redigitalization flags in inventory JSON."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
ROOT = _SCRIPT.parents[2]
sys.path.insert(0, str(ROOT))

from app_skeleton.api.document_library_service import (  # noqa: E402
    AUDIT_INVENTORY_JSON,
    INVENTORY_JSON,
    _lookup_processed_doc,
    _row_has_extracted_text,
    invalidate_cache,
    reconcile_vector_status,
)


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
    AUDIT_INVENTORY_JSON.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_INVENTORY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def reconcile(*, dry_run: bool = False) -> dict:
    rows = _load_inventory()
    stats = {
        "total": len(rows),
        "vector_status_updated": 0,
        "extraction_status_updated": 0,
        "processed_excerpt_promoted": 0,
    }
    for row in rows:
        processed = _lookup_processed_doc(row)
        if (
            (row.get("extraction_status") or "").strip() == "eligible_text"
            and not _row_has_extracted_text(row)
            and (processed.get("processed_excerpt") or "").strip()
        ):
            stats["processed_excerpt_promoted"] += 1
            if not dry_run:
                md = row.get("metadata_json") if isinstance(row.get("metadata_json"), dict) else {}
                md = dict(md)
                md["excerpt"] = processed["processed_excerpt"][:4000]
                md["promoted_from"] = "processed_twin"
                if processed.get("word_count"):
                    md["word_count"] = processed["word_count"]
                if processed.get("document_kind"):
                    md["document_kind"] = processed["document_kind"]
                if processed.get("extractor"):
                    md["extractor"] = processed["extractor"]
                row["metadata_json"] = md
                row["extraction_status"] = "extracted"

        before_vs = row.get("vector_status")
        after_vs = reconcile_vector_status(row, processed)
        if before_vs != after_vs:
            stats["vector_status_updated"] += 1
            if not dry_run:
                row["vector_status"] = after_vs

        ext = (row.get("extraction_status") or "").strip()
        if ext == "eligible_text" and _row_has_extracted_text(row):
            stats["extraction_status_updated"] += 1
            if not dry_run:
                row["extraction_status"] = "extracted"
        elif ext == "eligible_text" and not _row_has_extracted_text(row) and not dry_run:
            row["vector_status"] = "not_evaluated"
    changed = (
        stats["vector_status_updated"]
        or stats["extraction_status_updated"]
        or stats["processed_excerpt_promoted"]
    )
    if not dry_run and changed:
        _save_inventory(rows)
        invalidate_cache()
    stats["inventory_path"] = str(INVENTORY_JSON)
    stats["dry_run"] = dry_run
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(reconcile(dry_run=args.dry_run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
