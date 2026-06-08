#!/usr/bin/env python3
"""Extract pending files, deduplicate inventory, apply standard classification, write report."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
ROOT = _SCRIPT.parents[2]
sys.path.insert(0, str(ROOT))

from omeia.api.document_classification import (  # noqa: E402
    APP_PAGES,
    apply_duplicate_canonicalization,
    apply_standard_classification,
)
from omeia.api.document_library_service import (  # noqa: E402
    AUDIT_INVENTORY_JSON,
    INVENTORY_JSON,
    invalidate_cache,
)

LOGGER = logging.getLogger(__name__)
REPORT_DIR = ROOT / "reports" / "document_library_audit"
REPORT_MD = REPORT_DIR / "classification_report_by_page.md"
REPORT_JSON = REPORT_DIR / "classification_report_by_page.json"


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


def _fmt_size(n: int | float | None) -> str:
    if not n:
        return "0 B"
    n = int(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n} {unit}"
        n //= 1024
    return f"{n} TB"


def _doc_metadata_lines(row: dict) -> list[str]:
    md = row.get("metadata_json") if isinstance(row.get("metadata_json"), dict) else {}
    lines = [
        f"- **{row.get('filename') or '?'}** (`{row.get('asset_id')}`)",
        f"  - Path: `{row.get('logical_path')}`",
        f"  - Type: {row.get('standard_document_type') or row.get('asset_type')} | "
        f"Ext: {row.get('extension') or '—'} | Size: {_fmt_size(row.get('size_bytes'))}",
        f"  - Domain: {row.get('domain')} | Section: {row.get('section_hint')}",
        f"  - Extraction: {row.get('extraction_status')} | "
        f"Review: {row.get('review_status')} | Confidence: {row.get('assignment_confidence')}",
        f"  - Standard category: **{row.get('standard_category')}** → "
        f"**{row.get('standard_subcategory')}**",
    ]
    if row.get("project_hint"):
        lines.append(f"  - Project hint: {row.get('project_hint')}")
    if md.get("document_kind"):
        lines.append(f"  - Document kind: {md.get('document_kind')}")
    if md.get("word_count"):
        lines.append(f"  - Word count: {md.get('word_count')}")
    if md.get("char_count"):
        lines.append(f"  - Char count: {md.get('char_count')}")
    if md.get("extractor"):
        lines.append(f"  - Extractor: {md.get('extractor')}")
    if row.get("checksum_sha256"):
        lines.append(f"  - Checksum: `{row['checksum_sha256'][:16]}…`")
    if row.get("duplicate_status") == "canonical":
        lines.append("  - Duplicate group: **canonical copy**")
    return lines


def generate_report(rows: list[dict]) -> tuple[str, dict]:
    active = [r for r in rows if r.get("inventory_active", True)]
    inactive = [r for r in rows if not r.get("inventory_active", True)]

    page_lookup = {p["page_id"]: p for p in APP_PAGES}
    by_page: dict[str, list[dict]] = defaultdict(list)
    for row in active:
        page_id = row.get("primary_app_page") or "data_storage.all_files"
        by_page[page_id].append(row)

    # Order pages as in APP_PAGES, then unmapped.*
    ordered_ids = [p["page_id"] for p in APP_PAGES if not p.get("catch_all")]
    extra_ids = sorted(k for k in by_page if k not in ordered_ids and not k.startswith("unmapped."))
    unmapped_ids = sorted(k for k in by_page if k.startswith("unmapped."))
    page_order = ordered_ids + extra_ids + unmapped_ids

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_inventory_rows": len(rows),
        "active_unique_files": len(active),
        "duplicates_suppressed": len(inactive),
        "extraction": {},
        "document_types": defaultdict(int),
        "pages": [],
    }

    for status in ("not_started", "extracted", "metadata_only", "failed", "skipped"):
        summary["extraction"][status] = sum(1 for r in active if r.get("extraction_status") == status)

    for row in active:
        summary["document_types"][row.get("standard_document_type") or "unknown"] += 1
    summary["document_types"] = dict(sorted(summary["document_types"].items(), key=lambda x: -x[1]))

    lines: list[str] = [
        "# OMEIA Document Library — Classification Report by App Page",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "## Executive summary",
        "",
        f"| Metric | Count |",
        f"|--------|------:|",
        f"| Total inventory rows | {len(rows)} |",
        f"| Active files (duplicates removed from browse) | {len(active)} |",
        f"| Duplicate copies suppressed | {len(inactive)} |",
        f"| Not started extraction (active) | {summary['extraction'].get('not_started', 0)} |",
        f"| Extracted (active) | {summary['extraction'].get('extracted', 0)} |",
        f"| Metadata only (active) | {summary['extraction'].get('metadata_only', 0)} |",
        "",
        "### Standard document types (active files)",
        "",
    ]
    for dtype, count in summary["document_types"].items():
        lines.append(f"- **{dtype}**: {count}")

    lines.extend(["", "---", ""])

    for page_id in page_order:
        docs = by_page.get(page_id, [])
        if not docs:
            continue
        meta = page_lookup.get(page_id, {})
        main_label = meta.get("main_label") or page_id.split(".")[0].title()
        sub_label = meta.get("sub_label") or page_id
        lines.append(f"## {main_label} → {sub_label}")
        lines.append("")
        lines.append(f"**Page ID:** `{page_id}` | **Files:** {len(docs)}")
        lines.append("")

        by_cat: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        for doc in sorted(docs, key=lambda r: (r.get("standard_category") or "", r.get("standard_subcategory") or "", r.get("filename") or "")):
            cat = doc.get("standard_category") or "Unclassified"
            sub = doc.get("standard_subcategory") or "general"
            by_cat[cat][sub].append(doc)

        page_entry = {
            "page_id": page_id,
            "main_label": main_label,
            "sub_label": sub_label,
            "file_count": len(docs),
            "categories": [],
        }

        for cat in sorted(by_cat):
            cat_total = sum(len(v) for v in by_cat[cat].values())
            lines.append(f"### Category: {cat} ({cat_total} files)")
            lines.append("")
            cat_entry = {"name": cat, "file_count": cat_total, "subcategories": []}

            for sub in sorted(by_cat[cat]):
                sub_docs = by_cat[cat][sub]
                lines.append(f"#### Subcategory: {sub} ({len(sub_docs)} files)")
                lines.append("")
                cat_entry["subcategories"].append({
                    "name": sub,
                    "file_count": len(sub_docs),
                    "asset_ids": [d.get("asset_id") for d in sub_docs],
                })
                for doc in sub_docs:
                    lines.extend(_doc_metadata_lines(doc))
                    lines.append("")

            page_entry["categories"].append(cat_entry)

        summary["pages"].append(page_entry)
        lines.append("---")
        lines.append("")

    lines.extend([
        "## Duplicate copies suppressed",
        "",
        f"Total: **{len(inactive)}** files hidden from browse (point to canonical copy).",
        "",
    ])
    for row in sorted(inactive, key=lambda r: r.get("logical_path") or "")[:100]:
        lines.append(
            f"- `{row.get('logical_path')}` → canonical `{row.get('canonical_asset_id')}`"
        )
    if len(inactive) > 100:
        lines.append(f"- … and {len(inactive) - 100} more")

    md_text = "\n".join(lines)
    return md_text, summary


def run_pipeline(*, extract: bool, extract_limit: int | None, skip_report: bool) -> dict:
    stats: dict = {"steps": []}

    if extract:
        import importlib.util

        ext_path = ROOT / "scripts" / "digitalization" / "extract_pending_inventory.py"
        spec = importlib.util.spec_from_file_location("extract_pending_inventory", ext_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        ext_stats = mod.extract_pending(limit=extract_limit, dry_run=False)
        stats["steps"].append({"extract": ext_stats})
        LOGGER.info("Extraction done: %s", ext_stats)

    rows = _load_inventory()
    dup_stats = apply_duplicate_canonicalization(rows)
    apply_standard_classification(rows)
    _save_inventory(rows)
    invalidate_cache()
    stats["steps"].append({"deduplicate": dup_stats})

    active = sum(1 for r in rows if r.get("inventory_active", True))
    stats["active_files"] = active
    stats["total_rows"] = len(rows)

    if not skip_report:
        md_text, report_json = generate_report(rows)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_MD.write_text(md_text, encoding="utf-8")
        REPORT_JSON.write_text(json.dumps(report_json, indent=2, ensure_ascii=False), encoding="utf-8")
        stats["report_md"] = str(REPORT_MD)
        stats["report_json"] = str(REPORT_JSON)
        LOGGER.info("Report written: %s", REPORT_MD)

    return stats


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-extract", action="store_true", help="Skip extraction step")
    parser.add_argument("--extract-limit", type=int, default=None)
    parser.add_argument("--skip-report", action="store_true")
    args = parser.parse_args()
    stats = run_pipeline(
        extract=not args.no_extract,
        extract_limit=args.extract_limit,
        skip_report=args.skip_report,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
