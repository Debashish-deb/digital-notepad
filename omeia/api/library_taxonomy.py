"""Smart library taxonomy — UI scope chips aligned with filesystem reorganization."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from omeia.api.paths import BLUEPRINT_ROOT

TAXONOMY_JSON = BLUEPRINT_ROOT / "configs" / "document_library" / "smart_taxonomy.json"


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    if not TAXONOMY_JSON.is_file():
        return {"version": 0, "domain_tabs": [], "maintenance_views": [], "library_zones": []}
    return json.loads(TAXONOMY_JSON.read_text(encoding="utf-8"))


def get_domain_tab(tab_id: str | None) -> dict[str, Any] | None:
    if not tab_id:
        return None
    for tab in load_taxonomy().get("domain_tabs", []):
        if tab.get("id") == tab_id:
            return tab
    return None


def categorize_billing_path(path: str) -> str:
    """Mirror frontend ordersBillingCategories.js for smart_chip assignment."""
    p = (path or "").replace("\\", "/")
    lower = p.lower()
    file_name = p.split("/")[-1].lower()

    if "usernames_and_passwords" in lower:
        return "billing_finance"
    if p.startswith("HUS_money/"):
        return "billing_finance"
    if "ups" in file_name or "campusship" in file_name:
        return "shipping_ups"
    if "fedex" in file_name or lower.endswith("fedex account info.docx"):
        return "shipping_fedex"
    if "air waybills fedex" in lower:
        return "shipping_fedex"
    if "/ups/" in lower:
        return "shipping_ups"
    if "dna samples to copenhagen" in lower or "myriad" in lower:
        return "shipping_dna"
    if any(k in lower for k in ("shipment to us", "rarecyte", "usda", "proforma")):
        return "shipping_us_customs"
    if "booking_the_seminar_room" in lower:
        return "billing_finance"
    if "billing_and_delivery" in lower or "laskulomake" in lower:
        return "billing_finance"
    return "billing_finance"


def categorize_archive_path(path: str) -> str:
    p = (path or "").replace("\\", "/")
    lower = p.lower()
    if re.search(r"orders\s+20\d{2}", lower) or "orders_excels" in lower:
        return "yearly_orders"
    if any(k in lower for k in ("quote", "offer", "fisher", "bionordika", "qiagen")):
        return "quotes_offers"
    if "archive" in lower or "computer" in lower:
        return "archive_misc"
    return "archive_misc"


def assign_smart_chip(row: dict[str, Any]) -> str | None:
    section = (row.get("section_hint") or "").strip()
    logical = (row.get("logical_path") or row.get("original_path") or "").replace("\\", "/")
    rel = logical.split("/", 1)[-1] if "/" in logical else logical

    if section == "orders_billing":
        return categorize_billing_path(rel)
    if section == "orders_archive":
        return categorize_archive_path(rel)
    if section == "overview_research_materials":
        return "research_materials"
    if section.startswith("overview_"):
        return section.replace("overview_", "")
    if section == "social_misc":
        return "social"
    if section == "wet_lab_files" and row.get("protocol_category"):
        return str(row.get("protocol_category"))
    if section == "wet_lab_files" and row.get("reagent_category"):
        return str(row.get("reagent_category"))
    return None


def chip_filter_matches(row: dict[str, Any], chip_filter: dict[str, Any]) -> bool:
    if not chip_filter:
        return True
    if chip_filter.get("system_view") == "project_files":
        is_project = bool(row.get("project_hint")) or "projects/" in (row.get("logical_path") or "").lower()
        if not is_project:
            return False
    for key, val in chip_filter.items():
        if key == "system_view":
            continue
        if key == "smart_chip":
            if assign_smart_chip(row) != val:
                return False
            continue
        if key == "protocol_only":
            if val and not row.get("is_protocol"):
                return False
            continue
        if key == "reagents_only":
            if val and not row.get("is_reagent_panel"):
                return False
            continue
        row_val = row.get(key if key != "section" else "section_hint")
        if key == "domain" and row_val != val:
            return False
        elif key == "section" and row_val != val:
            return False
        elif key not in ("domain", "section", "smart_chip", "protocol_only", "reagents_only", "system_view"):
            if row.get(key) != val:
                return False
    return True


def compute_scope_chip_counts(
    rows: list[dict[str, Any]],
    domain_tab_id: str | None,
    *,
    base_filter_fn,
) -> list[dict[str, Any]]:
    """Count files per scope chip for a domain tab."""
    tab = get_domain_tab(domain_tab_id)
    if not tab:
        return []
    out: list[dict[str, Any]] = []
    for chip in tab.get("scope_chips", []):
        filt = chip.get("filter") or {}
        count = 0
        for row in rows:
            if not base_filter_fn(row):
                continue
            if chip_filter_matches(row, filt):
                count += 1
        out.append({
            "id": chip["id"],
            "label": chip["label"],
            "description": chip.get("description"),
            "count": count,
            "filter": filt,
            "nav_sub": chip.get("nav_sub"),
        })
    return out


WET_LAB_NAV_LABELS = {
    ("wet_lab", "files"): "Lab database files — wet-lab section only; CyCIF/t-CyCIF paths are excluded (see CyCIF nav).",
    ("wet_lab", "protocols"): "Wet-lab protocols — SOPs and protocol documents only; excludes CyCIF, spreadsheets, and reagent inventories.",
    ("wet_lab", "inventory"): "Reagents & panels — antibody panels, reagent lists, GeoMx/Xenium inventories; excludes CyCIF paths.",
}

CYCIF_NAV_LABELS = {
    ("cycif", "cycif_projects"): "CyCIF individual projects — staining plans, validation runs, and project templates.",
    ("cycif", "cycif_instructions"): "CyCIF instructions and SOPs — experiment planning and antibody scanning references.",
    ("cycif", "cycif_sectioning"): "CyCIF sectioning and H&E — sectioning orders and post-CyCIF H&E records.",
    ("cycif", "cycif_inventory"): "CyCIF antibody inventory — panel spreadsheets and antibody databases.",
    ("cycif", "cycif_protocols"): "CyCIF protocols and resources — spatial CyCIF and GeoMx/CyCIF experiment docs.",
}


def describe_nav_scope(main_id: str, sub_id: str) -> dict[str, Any] | None:
    """Structured library scope for AI assistants and API consumers."""
    preset = resolve_preset_from_nav(main_id, sub_id)
    if not preset:
        return None
    filters = preset.get("filters") or {}
    parts = [
        f"Navigation: {main_id}/{sub_id}",
        f"Domain tab: {preset.get('domain_tab')}",
        WET_LAB_NAV_LABELS.get((main_id, sub_id), preset.get("description") or ""),
    ]
    if filters.get("section"):
        parts.append(f"Section filter: {filters['section']}")
    if filters.get("protocol_only"):
        parts.append("Content scope: protocol/SOP documents only (is_protocol=true).")
    if filters.get("reagents_only"):
        parts.append("Content scope: reagent, antibody panel, and inventory files only (is_reagent_panel=true).")
    if filters.get("protocol_category"):
        parts.append(f"Protocol workflow: {filters['protocol_category']}")
    if filters.get("reagent_category"):
        parts.append(f"Reagent category: {filters['reagent_category']}")
    if filters.get("exclude_cycif"):
        parts.append("Excludes CyCIF/t-CyCIF paths (is_cycif_document); those files appear under CyCIF nav only.")
    if filters.get("cycif_only"):
        parts.append("CyCIF scope only: paths containing cycif/t-cycif/tcycif in logical_path.")
    if filters.get("app_page"):
        parts.append(f"CyCIF sub-tab page: {filters['app_page']}")
    nav_hint = WET_LAB_NAV_LABELS.get((main_id, sub_id)) or CYCIF_NAV_LABELS.get((main_id, sub_id))
    if nav_hint:
        parts[2] = nav_hint
    return {
        "main_id": main_id,
        "sub_id": sub_id,
        "domain_tab": preset.get("domain_tab"),
        "filters": filters,
        "label": preset.get("label"),
        "description": preset.get("description"),
        "scope_summary": " ".join(p for p in parts if p),
        "filter_fields": {
            "section": "Filesystem twin section (e.g. wet_lab_files).",
            "protocol_only": "When true, only protocol/SOP paths (is_protocol).",
            "protocol_category": "Workflow chip: proto_spatial, proto_staining, proto_tissue_processing, etc.",
            "reagents_only": "When true, only reagent/panel/inventory paths (is_reagent_panel).",
            "reagent_category": "Reagent chip: reagents_inventory, reagents_geomx, reagents_xenium, etc.",
            "smart_chip": "Orders/billing or archive sub-scope chip id.",
            "file_type": "Asset type facet (e.g. table_or_registry for spreadsheets).",
            "exclude_cycif": "When true, omit CyCIF/t-CyCIF paths from Oetlab/wet-lab views.",
            "cycif_only": "When true, only CyCIF-related paths (complement of exclude_cycif).",
            "app_page": "CyCIF sub-tab id (cycif.projects, cycif.protocols, etc.).",
        },
    }


def resolve_preset_from_nav(main_id: str, sub_id: str) -> dict[str, Any] | None:
    """Map sidebar nav → domain tab + default filters."""
    mapping = {
        ("overview", "onboarding"): ("overview", {"section": "overview_onboarding"}),
        ("overview", "guidelines"): ("overview", {"section": "overview_guidelines"}),
        ("overview", "documents_permits"): ("overview", {"section": "overview_documents"}),
        ("overview", "personnel"): ("overview", {"section": "overview_personnel"}),
        ("overview", "cleaning"): ("overview", {"section": "overview_cleaning"}),
        ("overview", "social"): ("overview", {"domain": "social_memory", "section": "social_misc"}),
        ("overview", "research_materials"): ("overview", {"section": "overview_research_materials"}),
        ("wet_lab", "files"): ("wet_lab", {"section": "wet_lab_files", "exclude_cycif": True}),
        ("wet_lab", "protocols"): ("wet_lab", {"section": "wet_lab_files", "protocol_only": True, "exclude_cycif": True}),
        ("wet_lab", "inventory"): ("wet_lab", {"section": "wet_lab_files", "reagents_only": True, "exclude_cycif": True}),
        ("cycif", "cycif_projects"): ("wet_lab", {"section": "wet_lab_files", "cycif_only": True, "app_page": "cycif.projects"}),
        ("cycif", "cycif_instructions"): ("wet_lab", {"section": "wet_lab_files", "cycif_only": True, "app_page": "cycif.instructions"}),
        ("cycif", "cycif_sectioning"): ("wet_lab", {"section": "wet_lab_files", "cycif_only": True, "app_page": "cycif.sectioning"}),
        ("cycif", "cycif_inventory"): ("wet_lab", {"section": "wet_lab_files", "cycif_only": True, "app_page": "cycif.inventory"}),
        ("cycif", "cycif_protocols"): ("wet_lab", {"section": "wet_lab_files", "cycif_only": True, "app_page": "cycif.protocols"}),
        ("orders", "billing"): ("orders", {"section": "orders_billing"}),
        ("orders", "archive"): ("orders", {"section": "orders_archive"}),
        ("orders", "orders"): ("orders", {"section": "orders_archive", "smart_chip": "yearly_orders"}),
        ("orders", "related"): ("orders", {"section": "orders_billing"}),
        ("data_storage", "documents"): ("all_files", {}),
        ("data_storage", "all_files"): ("all_files", {}),
    }
    key = (main_id, sub_id)
    if key not in mapping:
        return None
    domain_tab, filters = mapping[key]
    tab = get_domain_tab(domain_tab)
    return {
        "domain_tab": domain_tab,
        "filters": filters,
        "label": tab.get("label") if tab else domain_tab,
        "description": tab.get("description") if tab else "",
    }
