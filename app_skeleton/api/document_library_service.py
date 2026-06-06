"""Document library service — faceted search over vault/audit inventory."""
from __future__ import annotations

import csv
import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from app_skeleton.api.paths import BLUEPRINT_ROOT, DATABASE_ROOT

LOGGER = logging.getLogger(__name__)

INVENTORY_JSON = BLUEPRINT_ROOT / "app_skeleton" / "data" / "raw_asset_inventory.json"
AUDIT_INVENTORY_JSON = (
    BLUEPRINT_ROOT / "reports" / "document_library_audit" / "first_pass" / "document_inventory.json"
)
REDIGITALIZATION_CSV = (
    BLUEPRINT_ROOT / "reports" / "document_library_audit" / "second_pass" / "redigitalization_queue.csv"
)
DIGITALIZED_CSV = (
    BLUEPRINT_ROOT / "reports" / "document_library_audit" / "second_pass" / "digitalized_data_inventory.csv"
)
CATEGORY_CONFIG_DIR = BLUEPRINT_ROOT / "configs" / "document_library"

LARGE_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

DOMAIN_TAB_MAP = {
    "overview": {"administration", "social_memory"},
    "wet_lab": {"lab_operations"},
    "orders": {"orders_procurement"},
    "projects": {"project_workspace", "projects"},
}

SYSTEM_VIEWS = {
    "all_files": "All files",
    "recently_opened": "Recently opened",
    "pinned": "Pinned",
    "not_indexed": "Not indexed",
    "needs_redigitalization": "Needs redigitalization",
    "unknown_type": "Unknown type",
    "duplicates": "Duplicates",
    "large_files": "Large files",
    "wet_lab": "Wet lab files",
    "project_files": "Project files",
    "orders_billing": "Orders & billing",
}

SCIENTIFIC_KEYWORDS = {
    "assay": (
        "cycif", "tcycif", "immunofluorescence", "scrna", "sequencing", "geomx", "geomet",
        "xenium", "visium", "ihc", "merfish", "codex", "spatial", "multiplex",
    ),
    "tissue": (
        "ffpe", "frozen", "omentum", "adnexa", "tissue", "section", "organoid", "ovarian",
        "hgsoc", "endometri", "omentum", "biopsy", "specimen",
    ),
    "marker": (
        "antibody", "marker", "panel", "cd3", "cd8", "cd20", "pd-l1", "pdl1", "ki67",
        "panck", "dapi", "hoechst",
    ),
}

_PROJECT_CODE_RE = re.compile(
    r"\b(proj[_\s-]?(\d+)[_\s-]?(\d+)|p(\d{1,3})|space|eyemt|kras|hgsoc|ovca)\b",
    re.I,
)
_SAMPLE_ID_RE = re.compile(
    r"\b([A-Z]{1,3}\d{2,6}[A-Z]?\d*|sample[_\s-]?\d+|specimen[_\s-]?\d+)\b",
    re.I,
)
_YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")
_PLATFORM_RE = re.compile(
    r"\b(xenium|geomx|geomet|cycif|tcycif|visium|scrna|merfish|codex|ihc|spatial)\b",
    re.I,
)
_OWNER_RE = re.compile(
    r"\b([A-Z][a-z]+[_\s][A-Z][a-z]+|[A-Z][a-z]{3,})\b",
)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@lru_cache(maxsize=1)
def _load_redigitalization_ids() -> frozenset[str]:
    ids: set[str] = set()
    if not REDIGITALIZATION_CSV.is_file():
        return frozenset()
    with REDIGITALIZATION_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            path = (row.get("source_file_path") or "").strip()
            if path:
                ids.add(path)
    return frozenset(ids)


@lru_cache(maxsize=1)
def _load_digitalized_by_asset() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    if not DIGITALIZED_CSV.is_file():
        return out
    with DIGITALIZED_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            aid = (row.get("asset_id") or "").strip()
            if aid:
                out[aid] = row
    return out


def load_inventory_source() -> tuple[list[dict[str, Any]], str]:
    """Return (rows, source_label)."""
    for path, label in (
        (INVENTORY_JSON, "raw_asset_inventory"),
        (AUDIT_INVENTORY_JSON, "audit_inventory"),
    ):
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    return data, label
            except Exception as exc:
                LOGGER.warning("Failed reading %s: %s", path, exc)
    return [], "none"


def invalidate_cache() -> None:
    _enriched_inventory.cache_clear()
    _duplicate_info.cache_clear()
    _load_redigitalization_ids.cache_clear()
    _load_digitalized_by_asset.cache_clear()
    _processed_doc_lookup.cache_clear()


def _norm_path_key(value: str) -> str:
    return (value or "").replace("\\", "/").strip().lower()


def _store_processed_entry(lookup: dict[str, dict[str, Any]], key: str, entry: dict[str, Any]) -> None:
    if not key:
        return
    existing = lookup.get(key)
    if not existing:
        lookup[key] = entry
        return
    if len(entry.get("processed_excerpt") or "") > len(existing.get("processed_excerpt") or ""):
        lookup[key] = entry


@lru_cache(maxsize=1)
def _processed_doc_lookup() -> dict[str, dict[str, Any]]:
    """Index processed lab twins by logical path, relative path, and filename."""
    from app_skeleton.api.database_processor import load_processed_section, storage_key
    from app_skeleton.api.database_sections import DATABASE_SECTIONS
    from app_skeleton.api.paths import PUBLIC_PROCESSED_DIR

    lookup: dict[str, dict[str, Any]] = {}
    for section_id in DATABASE_SECTIONS:
        twin = load_processed_section(section_id)
        if not twin:
            pub_path = PUBLIC_PROCESSED_DIR / f"{storage_key(section_id)}.json"
            if pub_path.is_file():
                try:
                    twin = json.loads(pub_path.read_text(encoding="utf-8"))
                except Exception:
                    twin = None
        if not twin:
            continue
        relative_root = (twin.get("relative_root") or "").strip("/")
        docs: list[dict[str, Any]] = list(twin.get("document_index") or [])
        for block in (twin.get("content_library") or {}).get("sections") or []:
            docs.extend(block.get("documents") or [])

        for doc in docs:
            rel = (doc.get("path") or doc.get("name") or "").strip()
            if not rel:
                continue
            full = f"{relative_root}/{rel}".strip("/") if relative_root else rel
            entry = {
                "processed_title": (doc.get("title") or "").strip(),
                "processed_excerpt": (doc.get("excerpt") or "").strip(),
                "document_kind": doc.get("document_kind"),
                "word_count": doc.get("word_count"),
                "extractor": doc.get("extractor"),
                "processed_extraction_status": doc.get("extraction_status"),
                "processed_metadata": doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {},
                "section_id": section_id,
                "section_label": twin.get("section_label"),
            }
            for key in {_norm_path_key(full), _norm_path_key(rel), _norm_path_key(doc.get("name") or "")}:
                _store_processed_entry(lookup, key, entry)
    return lookup


def _lookup_processed_doc(row: dict[str, Any]) -> dict[str, Any]:
    lookup = _processed_doc_lookup()
    logical = row.get("logical_path") or ""
    filename = row.get("filename") or ""
    keys = [
        _norm_path_key(logical),
        _norm_path_key("/".join(logical.split("/")[1:]) if "/" in logical else logical),
        _norm_path_key(filename),
    ]
    for key in keys:
        hit = lookup.get(key)
        if hit:
            return hit
    return {}


def _extract_filename_metadata(filename: str, logical_path: str) -> dict[str, Any]:
    blob = f"{filename} {logical_path}"
    project_codes = sorted({m.group(0).replace(" ", "_") for m in _PROJECT_CODE_RE.finditer(blob)})
    sample_ids = sorted({m.group(0) for m in _SAMPLE_ID_RE.finditer(blob)})[:8]
    platforms = sorted({m.group(1).lower() for m in _PLATFORM_RE.finditer(blob)})
    years = sorted({m.group(1) for m in _YEAR_RE.finditer(blob)})
    people = sorted({m.group(0).replace("_", " ") for m in _OWNER_RE.finditer(filename)})[:4]
    return {
        "inferred_project_codes": project_codes,
        "inferred_sample_ids": sample_ids,
        "inferred_platforms": platforms,
        "inferred_years": years,
        "inferred_people": people,
    }


def _metadata_completeness(row: dict[str, Any]) -> int:
    checks = [
        bool(row.get("project_hint") or row.get("inferred_project_codes")),
        bool(row.get("category")),
        bool(row.get("subcategory")),
        bool(row.get("assay_tags") or row.get("inferred_platforms")),
        bool(row.get("tissue_tags")),
        bool(row.get("marker_tags")),
        bool(row.get("owner_hint") or row.get("inferred_people")),
        bool(row.get("processed_excerpt") or row.get("title")),
        bool(row.get("word_count")),
        row.get("digitalization_status") == "indexed",
    ]
    return int(round(100 * sum(1 for c in checks if c) / len(checks)))


@lru_cache(maxsize=1)
def _duplicate_info() -> tuple[dict[str, int], dict[str, list[str]]]:
    """checksum -> count; checksum -> asset_ids."""
    by_hash: dict[str, list[str]] = defaultdict(list)
    rows, _ = load_inventory_source()
    for row in rows:
        digest = (row.get("checksum_sha256") or "").strip()
        aid = row.get("asset_id") or ""
        if digest and aid:
            by_hash[digest].append(aid)
    counts = {h: len(ids) for h, ids in by_hash.items() if len(ids) > 1}
    return counts, dict(by_hash)


def _folder_category(logical_path: str) -> tuple[str, str, str]:
    parts = [p for p in (logical_path or "").split("/") if p.strip()]
    domain_folder = parts[0] if parts else ""
    category = parts[1] if len(parts) > 1 else ""
    subcategory = parts[2] if len(parts) > 2 else ""
    return domain_folder, category, subcategory


def _infer_scientific_tags(blob: str) -> dict[str, list[str]]:
    lower = blob.lower()
    out: dict[str, list[str]] = {"assay": [], "tissue": [], "marker": []}
    for field, keywords in SCIENTIFIC_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                out[field].append(kw)
    return out


def _digitalization_status(row: dict[str, Any], dig: dict[str, str] | None) -> str:
    ext = row.get("extraction_status") or ""
    if dig and dig.get("needs_redigitalization") == "True":
        return "needs_redigitalization"
    if ext in ("eligible_text", "extracted", "indexed"):
        return "indexed"
    if ext in ("eligible_pending_review", "metadata_only"):
        return "metadata_only"
    if ext == "failed":
        return "failed"
    if ext == "not_started":
        return "not_started"
    return ext or "unknown"


def _preview_status(row: dict[str, Any]) -> str:
    ext = row.get("extraction_status") or ""
    asset_type = row.get("asset_type") or ""
    if ext in ("eligible_text", "extracted", "indexed", "eligible_pending_review"):
        return "available"
    if asset_type in ("image", "presentation"):
        return "thumbnail"
    if asset_type == "table_or_registry":
        return "spreadsheet_summary"
    if ext == "not_started":
        return "missing"
    return "partial"


def _unknown_type(row: dict[str, Any]) -> bool:
    """Match audit definition: no extension / unknown_no_extension only."""
    asset_type = (row.get("asset_type") or "").lower()
    ext = (row.get("extension") or "").lower()
    return asset_type == "unknown_no_extension" or ext in ("[no_ext]", "")


_PROTOCOLS_ROOT = re.compile(r"^protocols(?:,\s*instructions)?/", re.I)
_PATIENT_ROOT = re.compile(r"^patient sample protocols/", re.I)


def _is_cycif_path(path: str) -> bool:
    lower = (path or "").lower().replace("\\", "/")
    return "cycif" in lower or "t-cycif" in lower or "tcycif" in lower


def _categorize_wet_lab_protocol_path(path: str) -> str | None:
    p = (path or "").replace("\\", "/")
    lower = p.lower()
    if _PATIENT_ROOT.search(p):
        file_name = p.split("/")[-1] if "/" in p else p
        if re.search(r"pome|pova", file_name, re.I):
            return "patient_omentum"
        if re.search(r"padn", file_name, re.I):
            return "patient_adnexa"
        if re.search(r"r(spl|bow|vagina|per|asc)", file_name, re.I):
            return "patient_other_sites"
        return "patient_misc"
    if _PROTOCOLS_ROOT.search(p) or lower.startswith("protocols"):
        rest = p[p.index("/") + 1 :] if "/" in p else p
        rest_lower = rest.lower()
        top_folder = rest.split("/")[0].lower() if "/" in rest else rest.lower()
        if "spatial" in top_folder or re.search(r"cycif|geomx|pickseq|lc-ms|tcycif", rest_lower, re.I):
            return "proto_spatial"
        if any(x in top_folder for x in ("tissue dissociation", "organoid", "ipdc")):
            return "proto_sample_prep"
        if top_folder == "anastasia" or re.search(r"tissue.fixation|tissue.processing|tissue_processing|ffpe", rest_lower, re.I):
            return "proto_tissue_processing"
        if "archive" in top_folder:
            return "proto_archive"
        if "evos" in top_folder or "reference" in top_folder:
            return "proto_imaging"
        if "scrna" in top_folder:
            return "proto_scrna"
        if re.search(r"flowcytometry|flow cytometry|immunofluorescence|\bif\b|staining", rest_lower, re.I):
            return "proto_staining"
        if re.search(r"steriliz|calibration|precipitation|troubleshoot|ph meter", rest_lower, re.I):
            return "proto_lab_ops"
        return "proto_general"
    if "orders for slides" in lower:
        return "slide_orders"
    return None


def _is_wet_lab_protocol_path(path: str) -> bool:
    return not _is_cycif_path(path) and _categorize_wet_lab_protocol_path(path) is not None


def _enrich_row(row: dict[str, Any]) -> dict[str, Any]:
    dig_map = _load_digitalized_by_asset()
    dup_counts, dup_groups = _duplicate_info()
    redig_paths = _load_redigitalization_ids()

    r = dict(row)
    aid = r.get("asset_id") or ""
    logical = r.get("logical_path") or ""
    filename = r.get("filename") or ""
    blob = f"{logical} {filename} {r.get('project_hint', '')} {r.get('section_hint', '')}"

    domain_folder, path_category, path_subcategory = _folder_category(logical)
    category = r.get("standard_category") or path_category
    subcategory = r.get("standard_subcategory") or path_subcategory
    rel_path = "/".join(logical.split("/")[1:]) if "/" in logical else logical
    protocol_category = _categorize_wet_lab_protocol_path(rel_path)
    is_protocol = _is_wet_lab_protocol_path(rel_path)
    dig = dig_map.get(aid)
    checksum = (r.get("checksum_sha256") or "").strip()
    dup_count = dup_counts.get(checksum, 0)
    stored_dup = (r.get("duplicate_status") or "").strip()

    original = r.get("original_path") or ""
    needs_redig = bool(dig and dig.get("needs_redigitalization") == "True") or original in redig_paths

    sci = _infer_scientific_tags(blob)
    inferred = _extract_filename_metadata(filename, logical)
    processed = _lookup_processed_doc(r)

    platforms = list(dict.fromkeys((sci["assay"] or []) + inferred.get("inferred_platforms", [])))
    enriched = r.get("enriched_metadata") or {}
    sm = enriched.get("suggested_metadata") or {}
    am = r.get("approved_metadata") or enriched.get("approved_metadata") or {}
    meta = {**sm, **am}
    title = meta.get("display_title") or processed.get("processed_title") or filename
    is_project_file = (logical or "").lower().startswith("projects/") or bool(meta.get("is_project_file"))
    if meta.get("cleaned_category") and not is_project_file:
        category = meta["cleaned_category"]
        if meta.get("cleaned_subcategory"):
            subcategory = meta["cleaned_subcategory"]
    owner_hint = None
    md_json = r.get("metadata_json")
    if isinstance(md_json, dict):
        owner_hint = md_json.get("owner") or md_json.get("author")
    if not owner_hint and inferred.get("inferred_people"):
        owner_hint = inferred["inferred_people"][0]

    project_hint = (r.get("project_hint") or "").strip()
    if not project_hint and inferred.get("inferred_project_codes"):
        project_hint = inferred["inferred_project_codes"][0]

    r.update({
        "title": title,
        "domain_folder": domain_folder,
        "category": category,
        "subcategory": subcategory,
        "file_type": r.get("asset_type") or r.get("extension") or "unknown",
        "digitalization_status": _digitalization_status(r, dig),
        "preview_status": _preview_status(r),
        "duplicate_status": stored_dup or ("duplicate" if dup_count > 1 else "unique"),
        "duplicate_group_size": dup_count if dup_count > 1 else (2 if stored_dup == "duplicate" else 1),
        "canonical_asset_id": r.get("canonical_asset_id"),
        "inventory_active": r.get("inventory_active", True),
        "standard_document_type": r.get("standard_document_type"),
        "primary_app_page": r.get("primary_app_page"),
        "duplicate_siblings": dup_groups.get(checksum, [])[:10] if dup_count > 1 else [],
        "unknown_type": meta.get("unknown_type") if "unknown_type" in meta else _unknown_type(r),
        "needs_redigitalization": needs_redig,
        "needs_review": (
            bool(meta.get("human_review_needed"))
            or meta.get("review_status") == "needs_human_review"
            or float(r.get("assignment_confidence") or 0) < 0.86
        ),
        "is_large": int(r.get("size_bytes") or 0) >= LARGE_FILE_BYTES,
        "assay_tags": platforms,
        "tissue_tags": sci["tissue"],
        "marker_tags": sci["marker"],
        "owner_hint": owner_hint,
        "inferred_project_codes": inferred.get("inferred_project_codes", []),
        "inferred_sample_ids": inferred.get("inferred_sample_ids", []),
        "inferred_platforms": inferred.get("inferred_platforms", []),
        "inferred_years": inferred.get("inferred_years", []),
        "inferred_people": inferred.get("inferred_people", []),
        "processed_excerpt": processed.get("processed_excerpt"),
        "document_kind": processed.get("document_kind"),
        "word_count": processed.get("word_count"),
        "extractor": processed.get("extractor"),
        "processed_section_label": processed.get("section_label"),
        "processed_metadata": processed.get("processed_metadata") or {},
        "redigitalization_reason": (dig or {}).get("redigitalization_reason"),
        "is_stale": (dig or {}).get("is_stale") == "True",
        "is_protocol": is_protocol,
        "protocol_category": protocol_category,
        "display_title": meta.get("display_title") or title,
        "short_title": meta.get("short_title"),
        "subtitle": meta.get("subtitle"),
        "document_role": meta.get("document_role"),
        "professional_role_label": meta.get("professional_role_label"),
        "path_breadcrumb": meta.get("path_breadcrumb"),
        "cleaned_domain": meta.get("cleaned_domain"),
        "search_aliases": meta.get("search_aliases") or [],
        "page_label": meta.get("page_label"),
        "primary_ui_badges": meta.get("primary_ui_badges") or [],
        "metadata_score": enriched.get("metadata_score") or r.get("metadata_score"),
        "metadata_grade": enriched.get("metadata_grade") or r.get("metadata_grade"),
        "review_status_meta": meta.get("review_status"),
        "is_project_file": meta.get("is_project_file", False),
        "project_category_original": meta.get("project_category_original"),
    })
    r["metadata_completeness"] = enriched.get("metadata_score") or _metadata_completeness(r)
    return r


@lru_cache(maxsize=1)
def _enriched_inventory() -> tuple[list[dict[str, Any]], str]:
    rows, source = load_inventory_source()
    return [_enrich_row(r) for r in rows], source


def get_enriched_rows() -> list[dict[str, Any]]:
    return list(_enriched_inventory()[0])


def get_stats() -> dict[str, Any]:
    rows = get_enriched_rows()
    _, source = _enriched_inventory()
    dup_counts, _ = _duplicate_info()

    not_started = sum(1 for r in rows if (r.get("extraction_status") or "") == "not_started")
    needs_redig = sum(1 for r in rows if r.get("needs_redigitalization"))
    unknown = sum(1 for r in rows if r.get("unknown_type"))
    dup_groups = len(dup_counts)
    dup_files = sum(c for c in dup_counts.values())
    not_indexed = sum(1 for r in rows if r.get("vector_status") in (None, "not_evaluated", ""))
    preview_missing = sum(1 for r in rows if r.get("preview_status") == "missing")
    large = sum(1 for r in rows if r.get("is_large"))

    domain_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        domain_counts[r.get("domain") or "unknown"] += 1

    active_rows = [r for r in rows if r.get("inventory_active", True) and r.get("duplicate_status") != "duplicate"]
    return {
        "total_files": len(active_rows),
        "total_inventory_rows": len(rows),
        "inventory_source": source,
        "audit_counts": {
            "not_started": not_started,
            "needs_redigitalization": needs_redig,
            "unknown_type": unknown,
            "duplicate_groups": dup_groups,
            "duplicate_files": dup_files,
            "not_indexed": not_indexed,
            "preview_missing": preview_missing,
            "large_files": large,
        },
        "domain_counts": dict(sorted(domain_counts.items(), key=lambda x: -x[1])),
        "system_views": SYSTEM_VIEWS,
    }


def _row_matches_system_view(row: dict[str, Any], view: str | None) -> bool:
    if not view or view == "all_files":
        return True
    if view == "not_indexed":
        return row.get("vector_status") in (None, "not_evaluated", "") or row.get("digitalization_status") == "not_started"
    if view == "needs_redigitalization":
        return bool(row.get("needs_redigitalization"))
    if view == "unknown_type":
        return bool(row.get("unknown_type"))
    if view == "duplicates":
        return row.get("duplicate_status") == "duplicate"
    if view == "large_files":
        return bool(row.get("is_large"))
    if view == "wet_lab":
        return row.get("domain") == "lab_operations" or row.get("section_hint") == "wet_lab_files"
    if view == "project_files":
        return bool(row.get("project_hint")) or "projects" in (row.get("logical_path") or "").lower()
    if view == "orders_billing":
        return row.get("section_hint") in ("orders_billing", "orders_archive") or row.get("domain") == "orders_procurement"
    return True


def _row_matches_domain_tab(row: dict[str, Any], tab: str | None) -> bool:
    if not tab or tab == "all_files":
        return True
    domains = DOMAIN_TAB_MAP.get(tab)
    if domains:
        return (row.get("domain") or "") in domains
    return True


def _tokenize_query(q: str) -> list[str]:
    return [t for t in re.split(r"\s+", (q or "").strip().lower()) if len(t) >= 2]


def _search_blob(row: dict[str, Any]) -> str:
    parts = [
        row.get("filename"),
        row.get("title"),
        row.get("logical_path"),
        row.get("domain"),
        row.get("section_hint"),
        row.get("project_hint"),
        row.get("asset_type"),
        row.get("extension"),
        row.get("category"),
        row.get("subcategory"),
        " ".join(row.get("assay_tags") or []),
        " ".join(row.get("tissue_tags") or []),
        " ".join(row.get("marker_tags") or []),
        row.get("owner_hint") or "",
        " ".join(row.get("inferred_project_codes") or []),
        " ".join(row.get("inferred_sample_ids") or []),
        " ".join(row.get("inferred_platforms") or []),
        row.get("processed_excerpt") or "",
        row.get("display_title") or "",
        " ".join(row.get("search_aliases") or []),
        row.get("document_role") or "",
        row.get("project_category_original") or "",
        row.get("page_label") or "",
        row.get("professional_role_label") or "",
        row.get("path_breadcrumb") or "",
        " ".join(row.get("primary_ui_badges") or []),
        row.get("cleaned_domain") or "",
    ]
    md = row.get("metadata_json")
    if isinstance(md, dict):
        parts.append(str(md.get("excerpt", "")))
    return " ".join(str(p) for p in parts if p).lower()


def _apply_filters(
    rows: list[dict[str, Any]],
    *,
    q: str,
    domain_tab: str | None,
    system_view: str | None,
    filters: dict[str, Any],
) -> list[tuple[float, dict[str, Any]]]:
    tokens = _tokenize_query(q)
    hits: list[tuple[float, dict[str, Any]]] = []

    include_duplicates = (
        system_view == "duplicates"
        or filters.get("duplicate_status") in ("duplicate", "canonical")
        or filters.get("include_duplicates") is True
    )

    for row in rows:
        if not _row_matches_domain_tab(row, domain_tab):
            continue
        if not _row_matches_system_view(row, system_view):
            continue
        if not include_duplicates and row.get("inventory_active") is False:
            continue
        if not include_duplicates and row.get("duplicate_status") == "duplicate":
            continue

        if filters.get("domain") and row.get("domain") != filters["domain"]:
            continue
        if filters.get("section") and row.get("section_hint") != filters["section"]:
            continue
        if filters.get("category") and row.get("category") != filters["category"]:
            continue
        if filters.get("subcategory") and row.get("subcategory") != filters["subcategory"]:
            continue
        if filters.get("file_type") and row.get("file_type") != filters["file_type"]:
            continue
        if filters.get("digitalization_status") and row.get("digitalization_status") != filters["digitalization_status"]:
            continue
        if filters.get("preview_status") and row.get("preview_status") != filters["preview_status"]:
            continue
        if filters.get("duplicate_status") and row.get("duplicate_status") != filters["duplicate_status"]:
            continue
        if filters.get("unknown_type") is True and not row.get("unknown_type"):
            continue
        if filters.get("project") and (row.get("project_hint") or "").lower() != filters["project"].lower():
            continue
        if filters.get("assay"):
            if filters["assay"] not in (row.get("assay_tags") or []):
                continue
        if filters.get("tissue"):
            if filters["tissue"] not in (row.get("tissue_tags") or []):
                continue
        if filters.get("marker"):
            if filters["marker"] not in (row.get("marker_tags") or []):
                continue
        if filters.get("protocol_only") and not row.get("is_protocol"):
            continue
        if filters.get("protocol_category") and row.get("protocol_category") != filters["protocol_category"]:
            continue
        if filters.get("modified_after"):
            dt = _parse_dt(row.get("modified_at"))
            cutoff = _parse_dt(filters["modified_after"])
            if not dt or not cutoff or dt < cutoff:
                continue
        if filters.get("modified_before"):
            dt = _parse_dt(row.get("modified_at"))
            cutoff = _parse_dt(filters["modified_before"])
            if not dt or not cutoff or dt > cutoff:
                continue

        blob = _search_blob(row)
        if tokens:
            fn = (row.get("filename") or "").lower()
            dt = (row.get("display_title") or "").lower()
            score = sum(
                5.0 if tok in fn else 4.0 if tok in dt else 1.0
                for tok in tokens if tok in blob
            )
            if score <= 0:
                continue
        else:
            score = 0.0
        hits.append((score, row))

    return hits


def _sort_hits(hits: list[tuple[float, dict[str, Any]]], sort: str, order: str) -> None:
    reverse = order != "asc"

    def key_fn(item: tuple[float, dict[str, Any]]):
        _, row = item
        if sort == "filename":
            return (row.get("filename") or "").lower()
        if sort == "size_bytes":
            return int(row.get("size_bytes") or 0)
        if sort == "modified_at":
            return row.get("modified_at") or ""
        if sort == "domain":
            return row.get("domain") or ""
        return item[0]

    hits.sort(key=key_fn, reverse=reverse)


def search_documents(
    *,
    q: str = "",
    domain_tab: str | None = None,
    system_view: str | None = None,
    filters: dict[str, Any] | None = None,
    sort: str = "filename",
    order: str = "asc",
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    rows = get_enriched_rows()
    filters = filters or {}
    hits = _apply_filters(rows, q=q, domain_tab=domain_tab, system_view=system_view, filters=filters)
    _sort_hits(hits, sort, order)
    total = len(hits)
    page = [h[1] for h in hits[offset : offset + limit]]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [_public_item(r) for r in page],
    }


def _public_item(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "asset_id", "filename", "title", "display_title", "short_title", "subtitle",
        "logical_path", "extension", "size_bytes",
        "domain", "section_hint", "project_hint", "asset_type", "file_type",
        "domain_folder", "category", "subcategory", "document_role",
        "professional_role_label", "path_breadcrumb", "cleaned_domain", "page_label",
        "is_project_file", "project_category_original",
        "digitalization_status", "preview_status", "duplicate_status",
        "duplicate_group_size", "unknown_type", "needs_redigitalization", "needs_review",
        "is_large", "assay_tags", "tissue_tags", "marker_tags",
        "inferred_project_codes", "inferred_sample_ids", "inferred_platforms",
        "owner_hint", "metadata_completeness", "metadata_score", "metadata_grade",
        "word_count", "document_kind",
        "modified_at", "indexed_at", "extraction_status", "vector_status", "review_status",
    )
    return {k: row.get(k) for k in keys}


def compute_facets(
    *,
    q: str = "",
    domain_tab: str | None = None,
    system_view: str | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = get_enriched_rows()
    filters = dict(filters or {})
    facet_fields = (
        "domain", "section_hint", "category", "subcategory", "file_type",
        "digitalization_status", "preview_status", "duplicate_status",
    )
    facets: dict[str, dict[str, int]] = {f: defaultdict(int) for f in facet_fields}
    project_counts: dict[str, int] = defaultdict(int)
    assay_counts: dict[str, int] = defaultdict(int)
    tissue_counts: dict[str, int] = defaultdict(int)
    marker_counts: dict[str, int] = defaultdict(int)
    unknown_count = 0

    base_filters = {k: v for k, v in filters.items() if k not in facet_fields}

    for row in rows:
        if not _row_matches_domain_tab(row, domain_tab):
            continue
        if not _row_matches_system_view(row, system_view):
            continue
        hits = _apply_filters([row], q=q, domain_tab=None, system_view=None, filters=base_filters)
        if not hits:
            continue

        for f in facet_fields:
            val = row.get("section_hint" if f == "section_hint" else f.replace("section", "section_hint") if f == "section" else f)
            if f == "section_hint":
                val = row.get("section_hint") or "unknown"
            elif f == "domain":
                val = row.get("domain") or "unknown"
            elif f == "category":
                val = row.get("category") or "unknown"
            elif f == "subcategory":
                val = row.get("subcategory") or "unknown"
            elif f == "file_type":
                val = row.get("file_type") or "unknown"
            elif f == "digitalization_status":
                val = row.get("digitalization_status") or "unknown"
            elif f == "preview_status":
                val = row.get("preview_status") or "unknown"
            elif f == "duplicate_status":
                val = row.get("duplicate_status") or "unknown"
            facets[f][str(val)] += 1

        if row.get("project_hint"):
            project_counts[row["project_hint"]] += 1
        for tag in row.get("assay_tags") or []:
            assay_counts[tag] += 1
        for tag in row.get("tissue_tags") or []:
            tissue_counts[tag] += 1
        for tag in row.get("marker_tags") or []:
            marker_counts[tag] += 1
        if row.get("unknown_type"):
            unknown_count += 1

    subcategories_by_category: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        if not _row_matches_domain_tab(row, domain_tab):
            continue
        if not _row_matches_system_view(row, system_view):
            continue
        hits = _apply_filters([row], q=q, domain_tab=None, system_view=None, filters=base_filters)
        if not hits:
            continue
        cat = row.get("category") or "unknown"
        sub = row.get("subcategory") or ""
        if sub:
            subcategories_by_category[cat][sub] += 1

    facet_out = {k: dict(sorted(v.items(), key=lambda x: -x[1])) for k, v in facets.items()}
    if "section_hint" in facet_out:
        facet_out["section"] = facet_out["section_hint"]

    selected_category = filters.get("category")
    if selected_category:
        facet_out["subcategory"] = dict(
            sorted(
                subcategories_by_category.get(selected_category, {}).items(),
                key=lambda x: -x[1],
            )
        )
    else:
        facet_out["subcategory"] = {}

    return {
        "facets": facet_out,
        "subcategories_by_category": {
            cat: dict(sorted(subs.items(), key=lambda x: -x[1]))
            for cat, subs in subcategories_by_category.items()
        },
        "project": dict(sorted(project_counts.items(), key=lambda x: -x[1])),
        "assay": dict(sorted(assay_counts.items(), key=lambda x: -x[1])),
        "tissue": dict(sorted(tissue_counts.items(), key=lambda x: -x[1])),
        "marker": dict(sorted(marker_counts.items(), key=lambda x: -x[1])),
        "unknown_type_count": unknown_count,
    }


def _try_live_excerpt(logical_path: str, filename: str) -> str | None:
    """Best-effort on-demand text extraction for preview (small text-friendly files only)."""
    if not logical_path or not DATABASE_ROOT.is_dir():
        return None
    ext = (Path(filename).suffix or "").lower()
    if ext not in {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx", ".pptx", ".ipynb"}:
        return None
    disk_path = DATABASE_ROOT / logical_path
    if not disk_path.is_file() or disk_path.stat().st_size > 8 * 1024 * 1024:
        return None
    try:
        from app_skeleton.api.document_extraction import _extract_file

        result = _extract_file(disk_path, DATABASE_ROOT)
        excerpt = (result.excerpt or "").strip()
        return excerpt[:4000] if excerpt else None
    except Exception as exc:
        LOGGER.debug("Live excerpt failed for %s: %s", logical_path, exc)
        return None


def get_preview(asset_id: str) -> dict[str, Any] | None:
    for row in get_enriched_rows():
        if row.get("asset_id") == asset_id:
            logical = row.get("logical_path") or ""
            preview_url = f"/database-static/{logical}" if logical and DATABASE_ROOT.is_dir() else None
            badges = []
            if row.get("digitalization_status") == "indexed":
                badges.append("Indexed")
            elif row.get("digitalization_status") == "not_started":
                badges.append("Not indexed")
            if row.get("preview_status") == "missing":
                badges.append("Preview missing")
            if row.get("duplicate_status") == "duplicate":
                badges.append("Duplicate")
            if row.get("unknown_type"):
                badges.append("Unknown type")
            if row.get("needs_review"):
                badges.append("Needs review")
            badges = badges[:3]

            md = row.get("metadata_json")
            excerpt = row.get("processed_excerpt") or None
            if isinstance(md, dict):
                excerpt = excerpt or md.get("excerpt")
            elif isinstance(md, str):
                try:
                    excerpt = excerpt or json.loads(md).get("excerpt")
                except Exception:
                    pass

            processed = _lookup_processed_doc(row)
            if not excerpt and processed.get("processed_excerpt"):
                excerpt = processed.get("processed_excerpt")
            if not excerpt:
                excerpt = _try_live_excerpt(logical, row.get("filename") or "")

            preview_type = row.get("preview_status") or "missing"
            proc_md = row.get("processed_metadata") or {}
            ext = (row.get("extension") or "").lower()
            fname = (row.get("filename") or "").lower()
            is_tiff = ext in {".tif", ".tiff"} or fname.endswith((".tif", ".tiff", ".ome.tif", ".ome.tiff"))
            image_meta = None
            thumb_url = None
            viewer_url = None
            if is_tiff:
                try:
                    from app_skeleton.api.image_streaming.image_metadata_service import ImageMetadataService

                    image_meta = ImageMetadataService().get_or_stub(
                        asset_id=asset_id,
                        filename=row.get("filename") or "",
                        extension=row.get("extension") or "",
                        size_bytes=int(row.get("size_bytes") or 0),
                    )
                    thumb_url = f"/api/assets/{asset_id}/image/thumbnail"
                    viewer_url = f"#viewer/image/{asset_id}"
                except Exception as exc:
                    LOGGER.debug("image preview enrichment failed for %s: %s", asset_id, exc)
            return {
                "asset_id": asset_id,
                "filename": row.get("filename"),
                "title": row.get("display_title") or row.get("title"),
                "display_title": row.get("display_title"),
                "subtitle": row.get("subtitle"),
                "document_role": row.get("document_role"),
                "metadata_score": row.get("metadata_score"),
                "metadata_grade": row.get("metadata_grade"),
                "logical_path": logical,
                "preview_url": preview_url,
                "preview_type": preview_type,
                "is_streamable_image": is_tiff,
                "image_metadata": image_meta,
                "thumbnail_url": thumb_url,
                "viewer_url": viewer_url,
                "excerpt": excerpt,
                "size_bytes": row.get("size_bytes"),
                "modified_at": row.get("modified_at"),
                "indexed_at": row.get("indexed_at"),
                "badges": badges,
                "metadata_completeness": row.get("metadata_completeness"),
                "metadata": {
                    "domain": row.get("domain"),
                    "section": row.get("section_hint"),
                    "section_label": row.get("processed_section_label"),
                    "category": row.get("project_category_original") or row.get("category"),
                    "subcategory": row.get("subcategory"),
                    "document_role": row.get("document_role"),
                    "page_label": row.get("page_label"),
                    "is_project_file": row.get("is_project_file"),
                    "domain_folder": row.get("domain_folder"),
                    "project": row.get("project_hint"),
                    "inferred_project_codes": row.get("inferred_project_codes"),
                    "inferred_sample_ids": row.get("inferred_sample_ids"),
                    "inferred_platforms": row.get("inferred_platforms"),
                    "inferred_years": row.get("inferred_years"),
                    "inferred_people": row.get("inferred_people"),
                    "owner": row.get("owner_hint"),
                    "file_type": row.get("file_type"),
                    "document_kind": row.get("document_kind"),
                    "extension": row.get("extension"),
                    "mime_type": row.get("mime_type"),
                    "checksum_sha256": row.get("checksum_sha256"),
                    "duplicate_group_size": row.get("duplicate_group_size"),
                    "duplicate_siblings": row.get("duplicate_siblings"),
                    "assay_tags": row.get("assay_tags"),
                    "tissue_tags": row.get("tissue_tags"),
                    "marker_tags": row.get("marker_tags"),
                    "digitalization_status": row.get("digitalization_status"),
                    "extraction_status": row.get("extraction_status"),
                    "vector_status": row.get("vector_status"),
                    "graph_status": row.get("graph_status"),
                    "review_status": row.get("review_status"),
                    "sensitivity_level": row.get("sensitivity_level"),
                    "assignment_confidence": row.get("assignment_confidence"),
                    "word_count": row.get("word_count"),
                    "extractor": row.get("extractor"),
                    "redigitalization_reason": row.get("redigitalization_reason"),
                    "is_stale": row.get("is_stale"),
                    "is_protocol": row.get("is_protocol"),
                    "protocol_category": row.get("protocol_category"),
                    "processed_metadata": proc_md,
                    "asset_id": asset_id,
                },
                "duplicate_warning": (
                    f"This file has {row.get('duplicate_group_size')} copies with the same checksum."
                    if row.get("duplicate_status") == "duplicate"
                    else None
                ),
            }
    return None


def load_category_trees() -> dict[str, Any]:
    trees: dict[str, Any] = {}
    for name in (
        "category_tree_official",
        "category_tree_folder_derived",
        "category_tree_tag_derived",
        "category_tree_scientific_terms",
        "category_tree_combined",
    ):
        path = CATEGORY_CONFIG_DIR / f"{name}.json"
        if path.is_file():
            try:
                trees[name] = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                trees[name] = {"error": str(exc)}
    return trees
