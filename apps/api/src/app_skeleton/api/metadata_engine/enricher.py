"""Per-file metadata enrichment pipeline."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app_skeleton.api.document_classification import (
    APP_PAGES,
    infer_standard_category,
    infer_standard_document_type,
    resolve_app_pages,
)
from app_skeleton.api.metadata_engine.constants import (
    NON_PROJECT_TAXONOMY,
    PROJECT_CATEGORY_NORMALIZE,
    SCIENTIFIC_PLATFORMS,
)
from app_skeleton.api.metadata_engine.display_titles import build_display_titles
from app_skeleton.api.metadata_engine.duplicates import apply_duplicate_plan
from app_skeleton.api.metadata_engine.scoring import metadata_grade, metadata_score
from app_skeleton.api.paths import DATABASE_ROOT

_PROJECT_ROOT_RE = re.compile(r"^projects/([^/]+)", re.I)
_JUNK_RE = re.compile(r"(?:^|/)\.(?:DS_Store|localized)$|thumbs\.db$|~\$", re.I)
_NO_EXT = {"", "[no_ext]", "unknown"}


def _path_parts(logical_path: str) -> list[str]:
    return [p for p in (logical_path or "").replace("\\", "/").split("/") if p.strip()]


def _parse_project_path(logical_path: str) -> dict[str, Any]:
    parts = _path_parts(logical_path)
    out: dict[str, Any] = {
        "is_project_file": False,
        "project_id": None,
        "project_name": None,
        "project_root": None,
        "project_category_original": None,
        "project_category_normalized": None,
        "project_folder_level_1": None,
        "project_folder_level_2": None,
        "project_folder_level_3": None,
        "project_relative_path": None,
        "do_not_change_project_category": False,
    }
    if not parts or parts[0].lower() != "projects":
        return out
    if len(parts) < 2:
        return out

    out["is_project_file"] = True
    out["project_id"] = parts[1]
    out["project_name"] = parts[1].replace("_", " ")
    out["project_root"] = f"projects/{parts[1]}"
    out["project_relative_path"] = "/".join(parts[2:]) if len(parts) > 2 else ""
    out["do_not_change_project_category"] = True

    if len(parts) > 2:
        raw_cat = parts[2]
        out["project_category_original"] = raw_cat
        out["project_category_normalized"] = PROJECT_CATEGORY_NORMALIZE.get(
            raw_cat.lower(), raw_cat
        )
        out["project_folder_level_1"] = raw_cat
    if len(parts) > 3:
        out["project_folder_level_2"] = parts[3]
    if len(parts) > 4:
        out["project_folder_level_3"] = parts[4]

    return out


def _infer_document_role(row: dict[str, Any], project_info: dict[str, Any]) -> tuple[str, float, str]:
    ext = (row.get("extension") or "").lower()
    asset_type = (row.get("asset_type") or "").lower()
    path = (row.get("logical_path") or "").lower()
    filename = (row.get("filename") or "").lower()

    if _JUNK_RE.search(path):
        return "system_artifact", 0.95, "path"

    std = infer_standard_document_type(row)
    mapping = {
        "protocol": "protocol",
        "sop": "SOP",
        "order_form": "order_form",
        "inventory_registry": "inventory",
        "project_plan": "project_plan",
        "lab_notebook": "lab_notebook",
        "figure": "figure",
        "presentation": "presentation",
        "spreadsheet": "spreadsheet",
        "image": "raw_image",
        "code_or_analysis": "analysis_notebook",
        "video": "unknown",
        "personnel": "personnel_document",
        "social_event": "social_event_document",
        "administrative": "administrative_document",
        "system_artifact": "system_artifact",
    }
    role = mapping.get(std, "unknown")

    if project_info.get("is_project_file"):
        cat = (project_info.get("project_category_original") or "").lower()
        if "presentation" in cat or ext in (".pptx", ".ppt", ".key"):
            role = "presentation"
        elif "writing" in cat:
            role = "manuscript" if "manuscript" in filename else "project_plan"
        elif cat == "log":
            role = "project_log"
        elif cat == "data":
            role = "dataset" if ext in (".h5", ".hdf5", ".zarr") else "spreadsheet"
        elif cat == "figures":
            role = "figure"
        elif "notebook" in cat or ext == ".ipynb":
            role = "analysis_notebook"

    confidence = 0.75 if role != "unknown" else 0.35
    source = "folder/path" if project_info.get("is_project_file") else "rule"
    return role, confidence, source


def _scientific_metadata(row: dict[str, Any], filename: str, path: str) -> dict[str, Any]:
    blob = f"{path} {filename}".lower()
    assay = []
    platform = []
    marker = []
    tissue = []
    sample_id = []

    for p in SCIENTIFIC_PLATFORMS:
        if p in blob:
            platform.append(p)
            assay.append(p)

    for kw in ("antibody", "panel", "cd3", "cd8", "pd-l1", "ki67", "dapi"):
        if kw in blob:
            marker.append(kw)
    for kw in ("ffpe", "frozen", "omentum", "adnexa", "ovarian", "hgsoc", "biopsy"):
        if kw in blob:
            tissue.append(kw)

    sample_m = re.findall(r"\b([A-Z]{1,3}\d{2,6}[A-Z]?\d*)\b", filename)
    sample_id = sample_m[:5]

    return {
        "assay": list(dict.fromkeys(assay)),
        "platform": list(dict.fromkeys(platform)),
        "marker_terms": marker,
        "tissue_or_site": tissue,
        "sample_id": sample_id,
    }


def _non_project_taxonomy(role: str, section: str, path: str) -> dict[str, str | None]:
    for domain, cats in NON_PROJECT_TAXONOMY.items():
        for cat, roles in cats.items():
            if role in roles:
                return {
                    "cleaned_domain": domain,
                    "cleaned_category": cat,
                    "cleaned_subcategory": role.replace("_", " ").title(),
                    "suggested_browse_group": domain,
                }
    section_label = section.replace("_", " ").title() if section else "General"
    folder_cat, folder_sub = infer_standard_category({"logical_path": path, "section_hint": section, "domain": ""})
    return {
        "cleaned_domain": "Lab Knowledge",
        "cleaned_category": section_label or folder_cat,
        "cleaned_subcategory": folder_sub,
        "suggested_browse_group": section_label,
    }


def _digitalization_block(row: dict[str, Any]) -> dict[str, Any]:
    ext_status = row.get("extraction_status") or ""
    md = row.get("metadata_json") if isinstance(row.get("metadata_json"), dict) else {}
    has_text = bool(md.get("excerpt") or md.get("char_count", 0) > 0)
    vector = row.get("vector_status") or "not_evaluated"
    has_embedding = vector in ("indexed", "embedded", "ready")

    preview = "available" if has_text else "missing"
    if (row.get("asset_type") or "") in ("image", "figure_or_plot", "presentation"):
        preview = "thumbnail" if not has_text else "available"

    indexed = has_text or has_embedding or ext_status in ("eligible_text", "extracted", "indexed")

    return {
        "extraction_status": ext_status,
        "extraction_method": md.get("extractor"),
        "has_text": has_text,
        "has_preview": preview != "missing",
        "has_thumbnail": (row.get("asset_type") or "") in ("image", "figure_or_plot"),
        "has_embedding": has_embedding,
        "has_summary": bool(md.get("excerpt")),
        "indexed_in_search": indexed,
        "vector_status": vector,
        "preview_status": preview,
        "OCR_needed": ext_status == "metadata_only" and (row.get("asset_type") == "image"),
        "needs_redigitalization": ext_status in ("not_started", "failed"),
    }


def _page_labels(page_ids: list[str]) -> tuple[str | None, str | None]:
    lookup = {p["page_id"]: p for p in APP_PAGES}
    if not page_ids:
        return None, None
    pid = page_ids[0]
    p = lookup.get(pid)
    if p:
        return pid, f"{p['main_label']} → {p['sub_label']}"
    return pid, pid


def enrich_inventory_row(
    row: dict[str, Any],
    *,
    duplicate_plans: dict[str, dict[str, Any]] | None = None,
    exists_locally: bool | None = None,
) -> dict[str, Any]:
    """Return full enrichment record with current/suggested/approved metadata."""
    logical = row.get("logical_path") or ""
    filename = row.get("filename") or ""
    parts = _path_parts(logical)
    project_info = _parse_project_path(logical)
    is_project = project_info["is_project_file"]

    folder_cat = parts[1] if parts and not is_project else (parts[2] if len(parts) > 2 else "")
    folder_sub = parts[2] if parts and not is_project and len(parts) > 2 else (parts[3] if len(parts) > 3 else "")

    if is_project:
        current_cat = project_info["project_category_original"]
        current_sub = project_info.get("project_folder_level_2") or ""
    else:
        current_cat, current_sub = infer_standard_category(row)

    role, role_conf, role_source = _infer_document_role(row, project_info)
    sci = _scientific_metadata(row, filename, logical)
    dig = _digitalization_block(row)
    page_ids = resolve_app_pages(row)
    page_id, page_label = _page_labels(page_ids)

    md_json = row.get("metadata_json") if isinstance(row.get("metadata_json"), dict) else {}
    processed_title = md_json.get("title") or md_json.get("document_kind")

    titles = build_display_titles(
        filename=filename,
        logical_path=logical,
        is_project_file=is_project,
        project_id=project_info.get("project_id"),
        project_category=project_info.get("project_category_normalized") or project_info.get("project_category_original"),
        document_role=role,
        processed_title=processed_title,
        metadata_excerpt=md_json.get("excerpt"),
    )

    dup_meta = apply_duplicate_plan(row, duplicate_plans or {})

    non_project = {}
    if not is_project:
        non_project = _non_project_taxonomy(role, row.get("section_hint") or "", logical)

    ext = (row.get("extension") or "").lower()
    unknown_type = (row.get("asset_type") == "unknown_no_extension") or ext in _NO_EXT

    confidence = min(0.95, 0.4 + role_conf * 0.3 + (0.2 if dig["has_text"] else 0) + float(row.get("assignment_confidence") or 0) * 0.2)
    review_status = (
        "auto_high_confidence" if confidence >= 0.82
        else "auto_medium_confidence" if confidence >= 0.6
        else "needs_human_review"
    )
    if unknown_type:
        review_status = "needs_human_review"

    suggested: dict[str, Any] = {
        # Identity
        "asset_id": row.get("asset_id"),
        "original_filename": filename,
        "normalized_filename": re.sub(r"[^a-zA-Z0-9._-]+", "_", filename),
        "original_path": logical,
        "canonical_path": logical,
        "source_domain": row.get("domain"),
        "source_section": row.get("section_hint"),
        "source_page": page_id,
        "source_folder": parts[0] if parts else "",
        "parent_folder": "/".join(parts[:-1]) if len(parts) > 1 else "",
        "file_extension": ext,
        "detected_file_type": row.get("asset_type"),
        "file_size": row.get("size_bytes"),
        "checksum_sha256": row.get("checksum_sha256"),
        "canonical_copy_asset_id": row.get("canonical_asset_id") or dup_meta.get("canonical_copy_asset_id"),
        "storage_location": row.get("storage_provider", "local_database_mirror"),
        "exists_locally": exists_locally if exists_locally is not None else True,
        # Display
        **titles,
        # Structural
        "is_project_file": is_project,
        "domain": row.get("domain"),
        "page_id": page_id,
        "page_label": page_label,
        "section": row.get("section_hint"),
        "current_category": current_cat,
        "current_subcategory": current_sub,
        "folder_category": folder_cat,
        "folder_subcategory": folder_sub,
        "category_confidence": round(confidence, 2),
        "category_source": "project_folder_rule" if is_project else role_source,
        "category_review_status": review_status,
        # Project overlay
        **project_info,
        # Non-project
        **non_project,
        # Scientific
        **sci,
        "document_role": role,
        # Digitalization
        **dig,
        # Quality
        "confidence_score": round(confidence, 2),
        "review_status": review_status,
        "unknown_type": unknown_type,
        "no_extension": ext in _NO_EXT,
        "system_artifact": role == "system_artifact",
        "temporary_file": bool(re.search(r"tmp|temp|~\\$", logical, re.I)),
        "duplicate_status": row.get("duplicate_status", "unique"),
        **dup_meta,
    }

    record = {
        "asset_id": row.get("asset_id"),
        "current_metadata": {
            k: row.get(k)
            for k in (
                "filename", "logical_path", "domain", "section_hint", "asset_type",
                "extension", "extraction_status", "duplicate_status", "project_hint",
            )
        },
        "suggested_metadata": suggested,
        "approved_metadata": row.get("approved_metadata") or {},
    }

    score, missing = metadata_score(record)
    record["metadata_score"] = score
    record["metadata_grade"] = metadata_grade(score)
    record["missing_metadata_fields"] = missing
    record["recommended_fix"] = (
        "Human review for unknown type" if unknown_type
        else ("Improve display title" if score < 50 else "No urgent fix")
    )

    return record


def enrich_all(
    rows: list[dict[str, Any]],
    *,
    duplicate_plans: dict[str, dict[str, Any]] | None = None,
    check_disk: bool = False,
) -> list[dict[str, Any]]:
    enriched = []
    for row in rows:
        exists = None
        if check_disk and row.get("logical_path"):
            exists = (DATABASE_ROOT / row["logical_path"]).is_file()
        enriched.append(
            enrich_inventory_row(row, duplicate_plans=duplicate_plans, exists_locally=exists)
        )
    return enriched
