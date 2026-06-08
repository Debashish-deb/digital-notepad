"""Lab database section roots (Overview, Orders, Social, etc.)."""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from omeia.api.paths import DATABASE_ROOT, safe_relative_path


class DatabaseSection(TypedDict):
    id: str
    label: str
    relative_root: str
    description: str


DATABASE_SECTIONS: dict[str, DatabaseSection] = {
    "overview_research_materials": {
        "id": "overview_research_materials",
        "label": "Research materials",
        "relative_root": "projects/RESEARCH MATERIALS",
        "description": "Abstracts, presentations, posters, and peer-review materials from disk.",
    },
    "overview_onboarding": {
        "id": "overview_onboarding",
        "label": "Onboarding & Outboarding",
        "relative_root": "Overview/Onboarding and Outboarding",
        "description": "Orientation, onboarding checklists, and outboarding procedures.",
    },
    "overview_guidelines": {
        "id": "overview_guidelines",
        "label": "Guidelines",
        "relative_root": "Overview/Guidelines",
        "description": "Research and work-related lab guidelines.",
    },
    "overview_documents": {
        "id": "overview_documents",
        "label": "Documents & Permits",
        "relative_root": "Overview/Documents - permits, forms, datasheets, handbooks etc.",
        "description": "Permits, forms, datasheets, handbooks, and compliance documents.",
    },
    "overview_personnel": {
        "id": "overview_personnel",
        "label": "Personnel",
        "relative_root": "Overview/PERSONNEL",
        "description": "Current personnel records and meeting support documents.",
    },
    "orders_billing": {
        "id": "orders_billing",
        "label": "Billing & ordering instructions",
        "relative_root": "ORDERS & RELATED INFORMATION/Billing and ordering instructions",
        "description": "Billing addresses, vendor accounts, shipments, and HUS billing.",
    },
    "orders_archive": {
        "id": "orders_archive",
        "label": "Archive",
        "relative_root": "ORDERS & RELATED INFORMATION/Archive",
        "description": "Historical orders, quotes, and archived procurement records.",
    },
    "meetings": {
        "id": "meetings",
        "label": "Meetings",
        "relative_root": "MEETINGS",
        "description": "Lab meetings, agendas, and minutes.",
    },
    "social_misc": {
        "id": "social_misc",
        "label": "Social & miscellaneous",
        "relative_root": "SOCIAL & MISCELLANEOUS",
        "description": "Lab parties, retreats, photos, outreach, and visitor records.",
    },
    "overview_cleaning": {
        "id": "overview_cleaning",
        "label": "Lab cleaning",
        "relative_root": "Overview/LAB CLEANING",
        "description": "Cleaning schedules and lab upkeep documents.",
    },
    "wet_lab_files": {
        "id": "wet_lab_files",
        "label": "Wet-lab files",
        "relative_root": "WET_LAB",
        "description": "Protocols, inventories, GeoMx/Xenium notes, and wet-lab spreadsheets.",
    },
}


def assert_all_section_roots_exist() -> list[str]:
    """Return section ids whose configured roots are missing on disk."""
    missing = []
    for sid, meta in DATABASE_SECTIONS.items():
        if not (DATABASE_ROOT / meta["relative_root"]).is_dir():
            missing.append(sid)
    return missing


def section_root(section_id: str) -> Path:
    meta = DATABASE_SECTIONS.get(section_id)
    if not meta:
        raise ValueError(f"Unknown database section: {section_id}")
    return safe_relative_path(DATABASE_ROOT, meta["relative_root"])


def list_sections() -> list[dict]:
    """Section metadata safe for API responses (no absolute disk paths)."""
    rows = []
    for meta in DATABASE_SECTIONS.values():
        root = DATABASE_ROOT / meta["relative_root"]
        rows.append({
            **meta,
            "exists": root.is_dir(),
            "logical_root": meta["relative_root"],
        })
    return rows
