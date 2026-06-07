#!/usr/bin/env python3
"""Reclassify empty extractions as metadata-only with searchable path/filename stubs."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
ROOT = _SCRIPT.parents[2]
sys.path.insert(0, str(ROOT))

from app_skeleton.api.document_library_service import (  # noqa: E402
    AUDIT_INVENTORY_JSON,
    INVENTORY_JSON,
    invalidate_cache,
    reconcile_vector_status,
)
from app_skeleton.api.document_extraction import _humanize_filename  # noqa: E402

_MAC_JUNK_RE = re.compile(r"/\._|^\._")


def _stub_excerpt(row: dict) -> str:
    path = (row.get("logical_path") or "").replace("\\", "/")
    name = Path(path).name
    title = _humanize_filename(name)
    parts = [p for p in path.split("/") if p and not p.startswith(".")]
    context = " / ".join(parts[-4:-1]) if len(parts) > 2 else ""
    lines = [f"Title: {title}", f"Path: {path}"]
    if context:
        lines.append(f"Folder: {context}")
    ext = (row.get("extension") or Path(name).suffix or "").lower()
    if ext:
        lines.append(f"Type: {ext.lstrip('.')}")
    size = row.get("size_bytes")
    if size:
        lines.append(f"Size: {size} bytes")
    lines.append("Note: No machine-readable text was extracted (likely scanned PDF, image, or empty file).")
    return "\n".join(lines)


def finalize(*, dry_run: bool = False) -> dict:
    rows = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    stats = {
        "total": len(rows),
        "metadata_only": 0,
        "skipped_junk": 0,
        "unchanged": 0,
        "dry_run": dry_run,
    }

    for row in rows:
        ext_status = (row.get("extraction_status") or "").strip()
        if ext_status != "empty":
            stats["unchanged"] += 1
            continue

        path = row.get("logical_path") or ""
        if _MAC_JUNK_RE.search(path) or Path(path).name.startswith("._"):
            stats["skipped_junk"] += 1
            if not dry_run:
                row["extraction_status"] = "skipped"
                row["inventory_active"] = False
                md = dict(row.get("metadata_json") or {})
                md["skip_reason"] = "macos_resource_fork"
                md["finalized_at"] = datetime.now(timezone.utc).isoformat()
                row["metadata_json"] = md
                row["vector_status"] = "metadata_summary_only"
            continue

        stats["metadata_only"] += 1
        if dry_run:
            continue

        md = dict(row.get("metadata_json") or {})
        stub = _stub_excerpt(row)
        md["excerpt"] = stub[:4000]
        md["char_count"] = len(stub)
        md["word_count"] = len(stub.split())
        md["document_kind"] = "metadata_stub"
        md["extractor"] = "filename_stub"
        md["empty_reason"] = "scanned_or_image_only"
        md["finalized_at"] = datetime.now(timezone.utc).isoformat()
        row["metadata_json"] = md
        row["extraction_status"] = "metadata_only"
        row["vector_status"] = reconcile_vector_status(row)

    if not dry_run and (stats["metadata_only"] or stats["skipped_junk"]):
        INVENTORY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        AUDIT_INVENTORY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        invalidate_cache()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(finalize(dry_run=args.dry_run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
