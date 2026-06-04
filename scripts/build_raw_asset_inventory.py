#!/usr/bin/env python3
"""Build a raw vault-style inventory from the local lab database mirror."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
from collections import Counter
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATABASE_ROOT = Path(os.environ.get("DATABASE_ROOT", str(ROOT.parent / "OMEIA-database"))).expanduser().resolve()
OUTPUT_DIR = ROOT / "app_skeleton" / "data"

TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".py", ".r", ".sh", ".json", ".yaml", ".yml",
    ".sql", ".csv", ".tsv", ".html", ".xml", ".css", ".js", ".jsx",
}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".dotx", ".rtf", ".odt"}
PRESENTATION_EXTENSIONS = {".pptx", ".ppt"}
TABLE_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".csv", ".tsv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".heic", ".svg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
CODE_EXTENSIONS = {".py", ".r", ".sh", ".js", ".jsx", ".ipynb", ".rmd"}

VECTORIZE_EXTENSIONS = (
    TEXT_EXTENSIONS | DOCUMENT_EXTENSIONS | PRESENTATION_EXTENSIONS | {".ipynb", ".rmd"}
)

SENSITIVE_PATH_HINTS = (
    "personnel", "hiring", "billing", "orders", "invoice", "quote", "permit",
    "biobank", "patient", "clinical", "registry", "ethics", "hus", "sample inventory",
)


def guess_mime_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == "[no_ext]" or not ext:
        return "application/octet-stream"
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"


def stable_id(relative_path: str, size_bytes: int) -> str:
    digest = hashlib.sha1(f"local_mirror:{relative_path}:{size_bytes}".encode("utf-8")).hexdigest()
    return f"asset_{digest[:16]}"


def classify_asset_type(path: Path) -> str:
    ext = path.suffix.lower()
    low = str(path).lower()
    if ext in CODE_EXTENSIONS:
        return "code_or_notebook"
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    if ext in PRESENTATION_EXTENSIONS:
        return "presentation"
    if ext in TABLE_EXTENSIONS:
        return "table_or_registry"
    if ext in IMAGE_EXTENSIONS:
        if any(h in low for h in ("figure", "figures", "plot", "plots", "visualization", "clustermap", "heatmap")):
            return "figure_or_plot"
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in {".dcc", ".rds", ".db", ".qpdata"}:
        return "analysis_binary_or_assay_artifact"
    if not ext:
        return "unknown_no_extension"
    return "other"


def guess_domain(relative_path: str) -> tuple[str, str | None, str | None, float]:
    parts = Path(relative_path).parts
    if not parts:
        return "unknown", None, None, 0.0
    top = parts[0]
    if top == "projects":
        if len(parts) > 1:
            return "project", parts[1], None, 0.72
        return "project", None, None, 0.40
    if top == "WET_LAB":
        return "lab_operations", None, "wet_lab_files", 0.90
    if top == "Overview":
        low = relative_path.lower()
        if "personnel" in low:
            return "administration", None, "overview_personnel", 0.88
        if "onboarding" in low or "outboarding" in low:
            return "administration", None, "overview_onboarding", 0.88
        if "guidelines" in low:
            return "administration", None, "overview_guidelines", 0.88
        if "documents" in low or "permits" in low or "forms" in low:
            return "administration", None, "overview_documents", 0.88
        if "lab cleaning" in low or "cleaning" in low:
            return "administration", None, "overview_cleaning", 0.88
        return "administration", None, "overview_general", 0.70
    if top == "ORDERS & RELATED INFORMATION":
        if "billing" in relative_path.lower():
            return "orders_procurement", None, "orders_billing", 0.92
        return "orders_procurement", None, "orders_archive", 0.86
    if top == "SOCIAL & MISCELLANEOUS":
        return "social_memory", None, "social_misc", 0.90
    return "unknown", None, None, 0.20


def guess_sensitivity(relative_path: str, asset_type: str) -> tuple[str, float]:
    low = relative_path.lower()
    if any(hint in low for hint in SENSITIVE_PATH_HINTS):
        if any(hint in low for hint in ("patient", "clinical", "registry", "biobank", "sample inventory")):
            return "restricted_or_clinical_review", 0.75
        return "internal_sensitive_review", 0.70
    if asset_type in {"image", "figure_or_plot", "presentation", "document"}:
        return "internal_review", 0.55
    return "unknown", 0.30


def vector_status(ext: str, asset_type: str) -> str:
    if ext in VECTORIZE_EXTENSIONS:
        return "eligible_pending_review"
    if asset_type in {"image", "figure_or_plot", "video", "analysis_binary_or_assay_artifact"}:
        return "metadata_summary_only"
    return "not_evaluated"


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def build_inventory(database_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    generated_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for path in sorted(database_root.rglob("*")):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        try:
            checksum = _sha256_file(path)
        except OSError:
            checksum = ""
        relative_path = str(path.relative_to(database_root))
        ext = path.suffix.lower()
        asset_type = classify_asset_type(path)
        domain, project_hint, section_hint, domain_conf = guess_domain(relative_path)
        sensitivity, sensitivity_conf = guess_sensitivity(relative_path, asset_type)
        confidence = round(min(max(domain_conf, 0.0), 1.0), 2)
        extraction_status = "not_started"
        if ext in VECTORIZE_EXTENSIONS:
            extraction_status = "eligible_text"
        elif asset_type in {"image", "figure_or_plot", "video", "analysis_binary_or_assay_artifact"}:
            extraction_status = "metadata_only"

        rows.append({
            "asset_id": stable_id(relative_path, stat.st_size),
            "original_path": str(path),
            "storage_provider": "local_database_mirror",
            "logical_path": relative_path,
            "filename": path.name,
            "extension": ext or "[no_ext]",
            "size_bytes": stat.st_size,
            "checksum_sha256": checksum,
            "mime_type": guess_mime_type(path),
            "extraction_status": extraction_status,
            "asset_type": asset_type,
            "domain": domain,
            "project_hint": project_hint or "",
            "section_hint": section_hint or "",
            "sensitivity_level": sensitivity,
            "assignment_confidence": confidence,
            "sensitivity_confidence": round(sensitivity_conf, 2),
            "review_status": "raw",
            "vector_status": vector_status(ext, asset_type),
            "graph_status": "not_asserted",
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "indexed_at": generated_at,
        })

    summary = {
        "generated_at": generated_at,
        "database_root": str(database_root),
        "asset_count": len(rows),
        "by_domain": dict(Counter(row["domain"] for row in rows).most_common()),
        "by_asset_type": dict(Counter(row["asset_type"] for row in rows).most_common()),
        "by_extension": dict(Counter(row["extension"] for row in rows).most_common()),
        "by_vector_status": dict(Counter(row["vector_status"] for row in rows).most_common()),
        "needs_review_count": sum(1 for row in rows if row["assignment_confidence"] < 0.86),
    }
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-root", type=Path, default=DATABASE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    rows, summary = build_inventory(args.database_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.output_dir / "raw_asset_inventory.json"
    csv_path = args.output_dir / "raw_asset_inventory.csv"
    summary_path = args.output_dir / "raw_asset_inventory_summary.json"

    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({
        "asset_count": len(rows),
        "json": str(json_path),
        "csv": str(csv_path),
        "summary": str(summary_path),
        "needs_review_count": summary["needs_review_count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
