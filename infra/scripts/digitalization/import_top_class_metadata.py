#!/usr/bin/env python3
"""Import human-reviewed top-class metadata CSVs into inventory approved_metadata."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
ROOT = _SCRIPT.parents[2]
sys.path.insert(0, str(ROOT))

from omeia.api.document_library_service import (  # noqa: E402
    AUDIT_INVENTORY_JSON,
    INVENTORY_JSON,
    invalidate_cache,
)

OUT_DIR = ROOT / "reports" / "document_library_audit" / "metadata_v2"
DEFAULT_TITLES = Path("/Users/debashishdeb/Downloads/display_title_mapping_top_class.csv")
DEFAULT_ENRICHED = Path("/Users/debashishdeb/Downloads/metadata_enriched_inventory_top_class.csv")


def _bool(val: str | None) -> bool:
    return str(val or "").strip().lower() in ("true", "1", "yes")


def _split_aliases(val: str | None) -> list[str]:
    if not val:
        return []
    return [a.strip() for a in val.split("|") if a.strip()]


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _approved_from_title(row: dict[str, str]) -> dict:
    improved = (row.get("improved_display_title") or row.get("display_title") or "").strip()
    short = (row.get("improved_short_title") or row.get("short_title") or improved[:48]).strip()
    return {
        "display_title": improved,
        "short_title": short,
        "subtitle": (row.get("display_subtitle") or "").strip() or None,
        "search_aliases": _split_aliases(row.get("search_aliases_enhanced") or row.get("search_aliases")),
        "document_role": (row.get("inferred_document_role") or "").strip(),
        "professional_role_label": (row.get("professional_role_label") or "").strip(),
        "confidence_score": float(row.get("confidence_revised") or row.get("confidence") or 0),
        "rename_needed": _bool(row.get("rename_needed_revised") or row.get("rename_needed")),
        "suggested_filename_for_later": (row.get("suggested_filename_for_later_review") or "").strip() or None,
        "ui_visibility_hint": (row.get("ui_visibility_hint") or "normal").strip(),
        "human_review_needed": _bool(row.get("human_review_needed")),
        "review_status": (
            "needs_human_review" if _bool(row.get("human_review_needed"))
            else "manually_reviewed"
        ),
        "title_issue_flags": (row.get("title_issue_flags") or "").strip() or None,
        "metadata_source": "top_class_display_title_mapping",
    }


def _approved_from_enriched(row: dict[str, str]) -> dict:
    badges = [b.strip() for b in (row.get("primary_ui_badges") or "").split(",") if b.strip()]
    return {
        "path_breadcrumb": (row.get("path_breadcrumb") or "").strip(),
        "cleaned_domain": (row.get("cleaned_domain_revised") or row.get("cleaned_domain") or "").strip(),
        "cleaned_category": (row.get("cleaned_category_revised") or row.get("cleaned_category") or "").strip(),
        "cleaned_subcategory": (row.get("cleaned_subcategory") or "").strip(),
        "classification_reason": (row.get("classification_reason_revised") or "").strip(),
        "page_id": (row.get("page_id") or "").strip(),
        "browse_visibility": (row.get("browse_visibility") or "normal").strip(),
        "metadata_score": int(float(row.get("metadata_score_revised") or row.get("metadata_score") or 0)),
        "metadata_grade": (row.get("metadata_grade_revised") or row.get("metadata_grade") or "").strip(),
        "recommended_action": (row.get("recommended_action") or "").strip(),
        "metadata_display_level": (row.get("metadata_display_level") or "normal_sleek").strip(),
        "primary_ui_badges": badges[:3],
        "preview_status": (row.get("preview_status_revised") or "").strip() or None,
        "unknown_type": _bool(row.get("unknown_type_revised") or row.get("unknown_type")),
        "indexed_in_search": _bool(row.get("indexed_in_search")),
        "duplicate_action_recommendation": (row.get("duplicate_action_recommendation") or "").strip(),
        "metadata_source": "top_class_enriched_inventory",
    }


def import_metadata(
    *,
    titles_csv: Path,
    enriched_csv: Path,
    copy_sources: bool = True,
) -> dict:
    if not titles_csv.is_file():
        raise FileNotFoundError(titles_csv)
    if not enriched_csv.is_file():
        raise FileNotFoundError(enriched_csv)

    titles_by_id = {r["asset_id"]: r for r in _load_csv(titles_csv) if r.get("asset_id")}
    enriched_by_id = {r["asset_id"]: r for r in _load_csv(enriched_csv) if r.get("asset_id")}

    rows = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    stats = {
        "inventory_rows": len(rows),
        "title_rows_applied": 0,
        "enriched_rows_applied": 0,
        "hidden_from_browse": 0,
        "missing_title_rows": 0,
        "project_files_title_only": 0,
    }

    for row in rows:
        aid = row.get("asset_id")
        if not aid:
            continue
        title_row = titles_by_id.get(aid)
        if not title_row:
            stats["missing_title_rows"] += 1
            continue

        approved = _approved_from_title(title_row)
        enriched_row = enriched_by_id.get(aid)
        logical = (row.get("logical_path") or "").lower()
        is_project = logical.startswith("projects/") or (row.get("domain") or "") == "project"

        if enriched_row and not is_project:
            approved.update(_approved_from_enriched(enriched_row))
            stats["enriched_rows_applied"] += 1
        elif is_project:
            stats["project_files_title_only"] += 1

        stats["title_rows_applied"] += 1

        visibility = approved.get("browse_visibility") or approved.get("ui_visibility_hint") or "normal"
        if visibility in ("hidden_admin_only", "hide_from_normal_browse_after_review"):
            row["inventory_active"] = False
            row["browse_visibility"] = visibility
            stats["hidden_from_browse"] += 1
        else:
            row.setdefault("inventory_active", True)

        row["approved_metadata"] = approved
        row["display_title"] = approved.get("display_title")
        row["metadata_score"] = approved.get("metadata_score") or row.get("metadata_score")
        row["metadata_grade"] = approved.get("metadata_grade") or row.get("metadata_grade")

        # Refresh enriched_metadata suggested layer for UI details drawer
        em = row.get("enriched_metadata") or {}
        sm = dict(em.get("suggested_metadata") or {})
        sm.update({k: v for k, v in approved.items() if v is not None})
        em["approved_metadata"] = approved
        em["suggested_metadata"] = sm
        em["metadata_score"] = approved.get("metadata_score") or em.get("metadata_score")
        em["metadata_grade"] = approved.get("metadata_grade") or em.get("metadata_grade")
        row["enriched_metadata"] = em

    INVENTORY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    AUDIT_INVENTORY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    invalidate_cache()

    if copy_sources:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(titles_csv, OUT_DIR / "display_title_mapping_top_class.csv")
        shutil.copy2(enriched_csv, OUT_DIR / "metadata_enriched_inventory_top_class.csv")

    stats["titles_csv"] = str(titles_csv)
    stats["enriched_csv"] = str(enriched_csv)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--titles", type=Path, default=DEFAULT_TITLES)
    parser.add_argument("--enriched", type=Path, default=DEFAULT_ENRICHED)
    parser.add_argument("--no-copy", action="store_true")
    args = parser.parse_args()
    stats = import_metadata(
        titles_csv=args.titles,
        enriched_csv=args.enriched,
        copy_sources=not args.no_copy,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
