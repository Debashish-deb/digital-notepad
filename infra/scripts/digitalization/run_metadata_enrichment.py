#!/usr/bin/env python3
"""Run metadata enrichment pipeline and emit all Phase 10 outputs (read-only, no file moves)."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
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
from omeia.api.metadata_engine.duplicates import (  # noqa: E402
    build_duplicate_groups,
    plan_lookup_by_asset,
)
from omeia.api.metadata_engine.enricher import enrich_all  # noqa: E402
from omeia.api.metadata_engine.scoring import metadata_grade  # noqa: E402

OUT_DIR = ROOT / "reports" / "document_library_audit" / "metadata_v2"
ENRICHED_JSON = OUT_DIR / "metadata_enriched_inventory.json"


def _load_rows() -> list[dict]:
    for path in (INVENTORY_JSON, AUDIT_INVENTORY_JSON):
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("inventory missing")


def _flat_csv_row(rec: dict) -> dict:
    sm = rec.get("suggested_metadata") or {}
    cm = rec.get("current_metadata") or {}
    return {
        "asset_id": rec.get("asset_id"),
        "original_filename": cm.get("filename") or sm.get("original_filename"),
        "logical_path": cm.get("logical_path") or sm.get("original_path"),
        "domain": sm.get("domain"),
        "section": sm.get("section"),
        "is_project_file": sm.get("is_project_file"),
        "project_id": sm.get("project_id"),
        "project_category_original": sm.get("project_category_original"),
        "display_title": sm.get("display_title"),
        "short_title": sm.get("short_title"),
        "document_role": sm.get("document_role"),
        "current_category": sm.get("current_category"),
        "current_subcategory": sm.get("current_subcategory"),
        "cleaned_domain": sm.get("cleaned_domain"),
        "cleaned_category": sm.get("cleaned_category"),
        "cleaned_subcategory": sm.get("cleaned_subcategory"),
        "page_id": sm.get("page_id"),
        "extraction_status": sm.get("extraction_status"),
        "indexed_in_search": sm.get("indexed_in_search"),
        "duplicate_status": sm.get("duplicate_status"),
        "duplicate_type": sm.get("duplicate_type"),
        "confidence_score": sm.get("confidence_score"),
        "review_status": sm.get("review_status"),
        "metadata_score": rec.get("metadata_score"),
        "metadata_grade": rec.get("metadata_grade"),
        "rename_needed": sm.get("rename_needed"),
        "unknown_type": sm.get("unknown_type"),
        "needs_redigitalization": sm.get("needs_redigitalization"),
    }


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def run(*, check_disk: bool = False) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inventory = _load_rows()
    dup_result = build_duplicate_groups(inventory)
    plan_by_asset = plan_lookup_by_asset(dup_result["plans"])

    enriched = enrich_all(inventory, duplicate_plans=plan_by_asset, check_disk=check_disk)

    # Persist enriched overlay on inventory rows (suggested only — no physical changes)
    by_id = {r["asset_id"]: r for r in inventory if r.get("asset_id")}
    for rec in enriched:
        aid = rec.get("asset_id")
        if aid and aid in by_id:
            by_id[aid]["enriched_metadata"] = rec
            by_id[aid]["display_title"] = rec["suggested_metadata"].get("display_title")
            by_id[aid]["metadata_score"] = rec.get("metadata_score")
            by_id[aid]["metadata_grade"] = rec.get("metadata_grade")

    INVENTORY_JSON.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    AUDIT_INVENTORY_JSON.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    ENRICHED_JSON.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")
    invalidate_cache()

    # CSV / queue outputs
    flat = [_flat_csv_row(r) for r in enriched]
    _write_csv(OUT_DIR / "metadata_enriched_inventory.csv", flat, list(flat[0].keys()) if flat else [])

    project_rows = [f for f in flat if f.get("is_project_file")]
    _write_csv(
        OUT_DIR / "project_metadata_overlay.csv",
        project_rows,
        list(project_rows[0].keys()) if project_rows else list(flat[0].keys()) if flat else [],
    )

    non_project = [f for f in flat if not f.get("is_project_file")]
    _write_csv(OUT_DIR / "non_project_clean_taxonomy.csv", non_project, list(non_project[0].keys()) if non_project else [])

    title_rows = [
        {
            "asset_id": r["asset_id"],
            "original_filename": r["suggested_metadata"]["original_filename"],
            "display_title": r["suggested_metadata"]["display_title"],
            "short_title": r["suggested_metadata"]["short_title"],
            "search_aliases": "|".join(r["suggested_metadata"].get("search_aliases") or []),
            "confidence": r["suggested_metadata"].get("confidence_score"),
            "rename_needed": r["suggested_metadata"].get("rename_needed"),
        }
        for r in enriched
    ]
    _write_csv(
        OUT_DIR / "display_title_mapping.csv",
        title_rows,
        ["asset_id", "original_filename", "display_title", "short_title", "search_aliases", "confidence", "rename_needed"],
    )

    rename_rows = [
        {
            "asset_id": r["asset_id"],
            "original_filename": r["suggested_metadata"]["original_filename"],
            "suggested_filename": r["suggested_metadata"].get("suggested_filename_for_later"),
            "rename_confidence": r["suggested_metadata"].get("rename_confidence"),
            "rename_reason": r["suggested_metadata"].get("rename_reason"),
        }
        for r in enriched
        if r["suggested_metadata"].get("rename_needed")
    ]
    _write_csv(
        OUT_DIR / "suggested_renames_for_later_review.csv",
        rename_rows,
        ["asset_id", "original_filename", "suggested_filename", "rename_confidence", "rename_reason"],
    )

    _write_csv(
        OUT_DIR / "duplicate_resolution_plan.csv",
        dup_result["plans"],
        [
            "duplicate_group_id", "canonical_asset_id", "duplicate_asset_ids", "duplicate_type",
            "duplicate_reason", "recommended_action", "safe_to_suppress_from_browse",
            "safe_to_delete_after_human_review", "keep_reason", "risk_level", "group_size",
        ],
    )

    _write_csv(
        OUT_DIR / "duplicate_review_queue.csv",
        dup_result["review_queue"],
        ["asset_id", "duplicate_group_id", "reason", "recommended_action"],
    )

    unknown_rows = [
        _flat_csv_row(r) for r in enriched
        if r["suggested_metadata"].get("unknown_type") or r["suggested_metadata"].get("no_extension")
    ]
    _write_csv(OUT_DIR / "unknown_type_review_queue.csv", unknown_rows, list(unknown_rows[0].keys()) if unknown_rows else [])

    low_conf = [_flat_csv_row(r) for r in enriched if r["suggested_metadata"].get("review_status") == "needs_human_review"]
    _write_csv(OUT_DIR / "low_confidence_metadata_queue.csv", low_conf, list(low_conf[0].keys()) if low_conf else [])

    redig = [
        _flat_csv_row(r) for r in enriched
        if r["suggested_metadata"].get("needs_redigitalization") or r["suggested_metadata"].get("OCR_needed")
    ]
    _write_csv(OUT_DIR / "redigitalization_priority_queue.csv", redig, list(redig[0].keys()) if redig else [])

    # Dashboard JSON
    scores = [r.get("metadata_score", 0) for r in enriched]
    grade_counts = Counter(metadata_grade(s) for s in scores)
    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_files": len(enriched),
        "project_files": sum(1 for r in enriched if r["suggested_metadata"].get("is_project_file")),
        "non_project_files": sum(1 for r in enriched if not r["suggested_metadata"].get("is_project_file")),
        "metadata_grade_counts": dict(grade_counts),
        "avg_metadata_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "unknown_type_count": len(unknown_rows),
        "low_confidence_count": len(low_conf),
        "duplicate_exact_groups": dup_result["exact_groups"],
        "duplicate_normalized_groups": dup_result["normalized_name_groups"],
        "safe_suppress_count": sum(
            1 for p in dup_result["plans"]
            if p.get("safe_to_suppress_from_browse") and p.get("duplicate_asset_ids")
            for _ in p["duplicate_asset_ids"]
        ),
        "duplicate_review_count": len(dup_result["review_queue"]),
        "rename_needed_count": len(rename_rows),
        "rename_not_needed_count": len(enriched) - len(rename_rows),
        "extraction_status": dict(Counter(r["suggested_metadata"].get("extraction_status") for r in enriched)),
        "document_roles": dict(Counter(r["suggested_metadata"].get("document_role") for r in enriched).most_common(20)),
    }
    (OUT_DIR / "metadata_quality_dashboard.json").write_text(
        json.dumps(dashboard, indent=2), encoding="utf-8"
    )

    # Smart views config
    smart_views = {
        "views": [
            {"id": "recently_opened", "label": "Recently opened", "type": "client_local"},
            {"id": "pinned", "label": "Pinned", "type": "client_local"},
            {"id": "needs_review", "label": "Needs review", "filter": {"review_status": "needs_human_review"}},
            {"id": "unknown_type", "label": "Unknown type", "filter": {"unknown_type": True}},
            {"id": "duplicates", "label": "Duplicate review", "filter": {"duplicate_status": "duplicate"}},
            {"id": "missing_preview", "label": "Missing preview", "filter": {"preview_status": "missing"}},
            {"id": "not_indexed", "label": "Not indexed", "filter": {"indexed_in_search": False}},
            {"id": "needs_redigitalization", "label": "Needs redigitalization", "filter": {"needs_redigitalization": True}},
            {"id": "large_files", "label": "Large files", "filter": {"is_large": True}},
            {"id": "system_artifacts", "label": "System artifacts", "filter": {"document_role": "system_artifact"}},
            {"id": "protocols_sops", "label": "Protocols & SOPs", "filter": {"document_role": ["protocol", "SOP", "instruction"]}},
            {"id": "inventories", "label": "Inventories & registries", "filter": {"document_role": ["inventory", "registry"]}},
            {"id": "figures_images", "label": "Figures & images", "filter": {"document_role": ["figure", "raw_image", "microscopy_image"]}},
            {"id": "spreadsheets", "label": "Spreadsheets", "filter": {"document_role": "spreadsheet"}},
            {"id": "presentations", "label": "Presentations", "filter": {"document_role": "presentation"}},
            {"id": "code_notebooks", "label": "Code & notebooks", "filter": {"document_role": ["code", "analysis_notebook"]}},
        ]
    }
    (OUT_DIR / "smart_views_config.json").write_text(json.dumps(smart_views, indent=2), encoding="utf-8")

    # Non-project taxonomy summary
    np_tax: dict[str, Counter] = defaultdict(Counter)
    for r in enriched:
        sm = r["suggested_metadata"]
        if sm.get("is_project_file"):
            continue
        dom = sm.get("cleaned_domain") or "Other"
        cat = sm.get("cleaned_category") or "General"
        np_tax[dom][cat] += 1

    summary_stats = {
        **dashboard,
        "non_project_taxonomy": {d: dict(c) for d, c in np_tax.items()},
        "output_dir": str(OUT_DIR),
    }

    _write_summary_md(summary_stats, dup_result, enriched)
    return summary_stats


def _write_summary_md(stats: dict, dup_result: dict, enriched: list[dict]) -> None:
    lines = [
        "# Metadata Improvement Summary",
        "",
        f"Generated: {stats['generated_at']}",
        "",
        "## Counts",
        f"- Total files processed: **{stats['total_files']}**",
        f"- Project files: **{stats['project_files']}** (folder categories preserved)",
        f"- Non-project files: **{stats['non_project_files']}**",
        f"- Improved display titles: **{stats['total_files']}** (all files received display_title)",
        f"- Original name already good (rename_needed=no): **{stats['rename_not_needed_count']}**",
        f"- Suggested renames for later review: **{stats['rename_needed_count']}**",
        f"- Exact duplicate SHA256 groups: **{stats['duplicate_exact_groups']}**",
        f"- Safe duplicate suppressions: **{stats['safe_suppress_count']}**",
        f"- Duplicate human review queue: **{stats['duplicate_review_count']}**",
        f"- Unknown/no-extension files: **{stats['unknown_type_count']}**",
        f"- Low-confidence metadata: **{stats['low_confidence_count']}**",
        f"- Average metadata score: **{stats['avg_metadata_score']}**",
        "",
        "## Metadata grades",
    ]
    for grade, count in sorted(stats["metadata_grade_counts"].items()):
        lines.append(f"- {grade}: {count}")

    lines.extend([
        "",
        "## Non-project browse structure (proposed)",
        "",
    ])
    for dom, cats in stats.get("non_project_taxonomy", {}).items():
        lines.append(f"### {dom}")
        for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
            lines.append(f"- {cat}: {n} files")

    lines.extend([
        "",
        "## Project folder policy",
        "- Project folder categories (plan, methods, data, writing, log, archive, etc.) were **not** changed.",
        "- Metadata enriches files **inside** existing project structure only.",
        "",
        "## Output files",
    ])
    for f in sorted(OUT_DIR.glob("*")):
        lines.append(f"- `{f}`")

    (OUT_DIR / "final_metadata_improvement_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-disk", action="store_true")
    args = parser.parse_args()
    stats = run(check_disk=args.check_disk)
    print(json.dumps({k: stats[k] for k in stats if k != "non_project_taxonomy"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
