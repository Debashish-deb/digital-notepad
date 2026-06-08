"""Standard document classification, page routing, and duplicate canonicalization."""
from __future__ import annotations

import re
from typing import Any, Callable

_JUNK_RE = re.compile(r"(?:^|/)\.(?:DS_Store|localized)$|thumbs\.db$", re.I)
_CYCIF_RE = re.compile(r"cycif|t-cycif|tcycif", re.I)


def _norm_path(path: str) -> str:
    return (path or "").replace("\\", "/").lower()


def _cycif_path(path: str) -> bool:
    return bool(_CYCIF_RE.search(_norm_path(path)))


def _protocol_path(path: str) -> bool:
    p = _norm_path(path)
    return "protocol" in p or "/sop" in p or p.endswith("sop")


def _cycif_projects_path(path: str) -> bool:
    p = _norm_path(path)
    if not _cycif_path(path):
        return False
    return any(
        x in p
        for x in (
            "individual",
            "tcycif_individual",
            "staining plan",
            "staining_plan",
            "project",
        )
    )


def _cycif_instructions_path(path: str) -> bool:
    p = _norm_path(path)
    return _cycif_path(path) and any(x in p for x in ("instruction", "template", "workflow", "planning"))


def _cycif_sectioning_path(path: str) -> bool:
    p = _norm_path(path)
    return _cycif_path(path) and any(x in p for x in ("section", "h&e", "h_e", "slide order"))


def _cycif_inventory_path(path: str) -> bool:
    p = _norm_path(path)
    return _cycif_path(path) and any(x in p for x in ("antibody", "panel", "inventory", "reagent"))


def _cycif_protocols_path(path: str) -> bool:
    p = _norm_path(path)
    return _cycif_path(path) and "protocol" in p


# Mirrors navigation.js + documentExplorerPresets.js (document-library pages only).
APP_PAGES: list[dict[str, Any]] = [
    {
        "page_id": "overview.onboarding",
        "main_label": "Overview",
        "sub_label": "Onboarding & Outboarding",
        "section_hints": {"overview_onboarding"},
    },
    {
        "page_id": "overview.guidelines",
        "main_label": "Overview",
        "sub_label": "Guidelines",
        "section_hints": {"overview_guidelines"},
    },
    {
        "page_id": "overview.documents",
        "main_label": "Overview",
        "sub_label": "Documents & Permits",
        "section_hints": {"overview_documents"},
    },
    {
        "page_id": "overview.personnel",
        "main_label": "Overview",
        "sub_label": "Personnel",
        "section_hints": {"overview_personnel"},
    },
    {
        "page_id": "overview.cleaning",
        "main_label": "Overview",
        "sub_label": "Lab cleaning",
        "section_hints": {"overview_cleaning"},
    },
    {
        "page_id": "overview.social",
        "main_label": "Overview",
        "sub_label": "Social & miscellaneous",
        "section_hints": {"social_misc"},
        "domains": {"social_memory"},
    },
    {
        "page_id": "overview.get_started",
        "main_label": "Overview",
        "sub_label": "General lab information",
        "section_hints": {"overview_general", "overview_get_started"},
    },
    {
        "page_id": "wet_lab.files",
        "main_label": "Wet-lab",
        "sub_label": "Lab database files",
        "section_hints": {"wet_lab_files"},
        "domains": {"lab_operations"},
        "exclude_path": _cycif_path,
    },
    {
        "page_id": "wet_lab.protocols",
        "main_label": "Wet-lab",
        "sub_label": "Wet-lab protocols",
        "section_hints": {"wet_lab_files"},
        "domains": {"lab_operations"},
        "path_match": _protocol_path,
        "exclude_path": _cycif_path,
    },
    {
        "page_id": "wet_lab.inventory",
        "main_label": "Wet-lab",
        "sub_label": "Reagents & panels",
        "section_hints": {"wet_lab_files"},
        "domains": {"lab_operations"},
        "path_match": lambda p: any(x in _norm_path(p) for x in ("inventory", "antibody", "panel", "reagent", "geomx", "xenium")),
        "exclude_path": _cycif_path,
    },
    {
        "page_id": "cycif.projects",
        "main_label": "CyCif",
        "sub_label": "Individual Projects",
        "section_hints": {"wet_lab_files"},
        "path_match": _cycif_projects_path,
    },
    {
        "page_id": "cycif.instructions",
        "main_label": "CyCif",
        "sub_label": "Instructions & SOPs",
        "section_hints": {"wet_lab_files"},
        "path_match": _cycif_instructions_path,
    },
    {
        "page_id": "cycif.sectioning",
        "main_label": "CyCif",
        "sub_label": "Sectioning & H&E",
        "section_hints": {"wet_lab_files"},
        "path_match": _cycif_sectioning_path,
    },
    {
        "page_id": "cycif.inventory",
        "main_label": "CyCif",
        "sub_label": "Antibody Inventory",
        "section_hints": {"wet_lab_files"},
        "path_match": _cycif_inventory_path,
    },
    {
        "page_id": "cycif.protocols",
        "main_label": "CyCif",
        "sub_label": "Protocols & Resources",
        "section_hints": {"wet_lab_files"},
        "path_match": _cycif_protocols_path,
    },
    {
        "page_id": "orders.billing",
        "main_label": "Orders & related information",
        "sub_label": "Billing & ordering instructions",
        "section_hints": {"orders_billing"},
        "domains": {"orders_procurement"},
    },
    {
        "page_id": "orders.archive",
        "main_label": "Orders & related information",
        "sub_label": "Archive",
        "section_hints": {"orders_archive"},
        "domains": {"orders_procurement"},
    },
    {
        "page_id": "projects.portfolio",
        "main_label": "Project Portfolio",
        "sub_label": "Project files",
        "domains": {"project"},
    },
    {
        "page_id": "data_storage.all_files",
        "main_label": "Data & Storage",
        "sub_label": "All Files (full library)",
        "catch_all": True,
    },
]

STANDARD_DOCUMENT_TYPES = (
    "protocol",
    "sop",
    "order_form",
    "inventory_registry",
    "project_plan",
    "lab_notebook",
    "administrative",
    "personnel",
    "social_event",
    "figure",
    "presentation",
    "spreadsheet",
    "image",
    "code_or_analysis",
    "video",
    "unknown",
    "system_artifact",
)


def _folder_parts(logical_path: str) -> tuple[str, str, str]:
    parts = [p for p in (logical_path or "").split("/") if p.strip()]
    return (
        parts[0] if parts else "",
        parts[1] if len(parts) > 1 else "",
        parts[2] if len(parts) > 2 else "",
    )


def infer_standard_document_type(row: dict[str, Any]) -> str:
    path = _norm_path(row.get("logical_path") or "")
    filename = _norm_path(row.get("filename") or "")
    asset_type = (row.get("asset_type") or "").lower()
    ext = (row.get("extension") or "").lower()

    if _JUNK_RE.search(path) or filename in (".ds_store", "thumbs.db"):
        return "system_artifact"

    if asset_type == "figure_or_plot" or ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg"):
        return "figure"
    if asset_type == "presentation" or ext in (".ppt", ".pptx", ".key"):
        return "presentation"
    if asset_type == "table_or_registry" or ext in (".xlsx", ".xls", ".csv", ".tsv"):
        if any(x in path for x in ("order", "billing", "purchase", "quote")):
            return "order_form"
        if any(x in path for x in ("inventory", "antibody", "panel", "reagent")):
            return "inventory_registry"
        return "spreadsheet"
    if asset_type == "video" or ext in (".mp4", ".mov", ".avi"):
        return "video"
    if asset_type == "code_or_notebook" or ext in (".py", ".r", ".ipynb", ".sh"):
        return "code_or_analysis"
    if asset_type == "image":
        return "image"
    if asset_type == "unknown_no_extension":
        return "unknown"

    if (row.get("domain") or "") == "social_memory":
        return "social_event"
    if (row.get("section_hint") or "") == "overview_personnel":
        return "personnel"
    if (row.get("section_hint") or "").startswith("orders"):
        return "order_form"
    if _protocol_path(path):
        return "protocol" if "protocol" in path else "sop"
    if (row.get("domain") or "") == "project":
        if any(x in path for x in ("plan", "proposal", "timeline")):
            return "project_plan"
        if any(x in path for x in ("notebook", "log", "notes")):
            return "lab_notebook"
    if (row.get("domain") or "") == "administration":
        return "administrative"

    return "unknown"


def infer_standard_category(row: dict[str, Any]) -> tuple[str, str]:
    """Return (standard_category, standard_subcategory) from path + domain."""
    domain_folder, category, subcategory = _folder_parts(row.get("logical_path") or "")
    section = (row.get("section_hint") or "").strip()
    dom = (row.get("domain") or "").strip()

    if dom == "project":
        return category or "Unassigned project folder", subcategory or "root"
    if section:
        section_label = section.replace("_", " ").title()
        if category:
            return section_label, category
        return section_label, subcategory or "general"
    if domain_folder:
        return domain_folder, category or subcategory or "general"
    return "Unclassified", "general"


def resolve_app_pages(row: dict[str, Any]) -> list[str]:
    """Return ordered page_ids this file appears on (primary first)."""
    section = (row.get("section_hint") or "").strip()
    dom = (row.get("domain") or "").strip()
    path = row.get("logical_path") or ""
    matched: list[str] = []

    for page in APP_PAGES:
        if page.get("catch_all"):
            continue
        sections = page.get("section_hints") or set()
        domains = page.get("domains") or set()
        if sections and section not in sections:
            continue
        if domains and dom not in domains:
            continue
        exclude: Callable[[str], bool] | None = page.get("exclude_path")
        if exclude and exclude(path):
            continue
        path_match: Callable[[str], bool] | None = page.get("path_match")
        if path_match and not path_match(path):
            continue
        matched.append(page["page_id"])

    if not matched:
        if dom == "project":
            matched.append("projects.portfolio")
        elif section:
            matched.append(f"unmapped.{section}")
        else:
            matched.append("data_storage.all_files")
    return matched


def _canonical_score(row: dict[str, Any]) -> int:
    path = (row.get("logical_path") or "").lower()
    score = 0
    ext_status = row.get("extraction_status") or ""
    if ext_status in ("extracted", "indexed", "eligible_text"):
        score += 100
    elif ext_status == "metadata_only":
        score += 60
    elif ext_status not in ("failed", "skipped", "not_started"):
        score += 30

    md = row.get("metadata_json")
    if isinstance(md, dict) and (md.get("excerpt") or md.get("char_count", 0) > 0):
        score += 40

    score += int(float(row.get("assignment_confidence") or 0) * 20)
    score -= min(len(path) // 10, 25)

    if _JUNK_RE.search(path) or path.endswith(".ds_store"):
        score -= 200
    if "/copy" in path or " copy" in path or re.search(r"\(\d+\)", path):
        score -= 15
    return score


def pick_canonical_asset(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return max(rows, key=lambda r: (_canonical_score(r), -(len(r.get("logical_path") or ""))))


def apply_duplicate_canonicalization(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Mark duplicates; keep one canonical copy per checksum. Returns stats."""
    by_hash: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        digest = (row.get("checksum_sha256") or "").strip()
        if digest:
            by_hash.setdefault(digest, []).append(row)

    stats = {"groups": 0, "duplicates_marked": 0, "canonical_marked": 0, "unique": 0}

    for digest, group in by_hash.items():
        if len(group) == 1:
            group[0]["duplicate_status"] = "unique"
            group[0]["canonical_asset_id"] = group[0].get("asset_id")
            group[0]["inventory_active"] = True
            stats["unique"] += 1
            continue

        stats["groups"] += 1
        canonical = pick_canonical_asset(group)
        cid = canonical.get("asset_id")
        for row in group:
            aid = row.get("asset_id")
            if aid == cid:
                row["duplicate_status"] = "canonical"
                row["canonical_asset_id"] = cid
                row["inventory_active"] = True
                stats["canonical_marked"] += 1
            else:
                row["duplicate_status"] = "duplicate"
                row["canonical_asset_id"] = cid
                row["inventory_active"] = False
                stats["duplicates_marked"] += 1

    # Rows without checksum stay active.
    for row in rows:
        if not (row.get("checksum_sha256") or "").strip():
            row.setdefault("duplicate_status", "unique")
            row.setdefault("canonical_asset_id", row.get("asset_id"))
            row.setdefault("inventory_active", True)

    return stats


def apply_standard_classification(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        if row.get("inventory_active") is False:
            continue
        cat, sub = infer_standard_category(row)
        row["standard_category"] = cat
        row["standard_subcategory"] = sub
        row["standard_document_type"] = infer_standard_document_type(row)
        row["app_page_ids"] = resolve_app_pages(row)
        row["primary_app_page"] = (row["app_page_ids"] or ["data_storage.all_files"])[0]
