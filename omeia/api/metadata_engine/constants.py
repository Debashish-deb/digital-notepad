"""Controlled vocabularies and non-project taxonomy proposals."""
from __future__ import annotations

DOCUMENT_ROLES = (
    "protocol",
    "SOP",
    "instruction",
    "inventory",
    "registry",
    "order_form",
    "invoice",
    "receipt",
    "shipping_document",
    "permit",
    "safety_document",
    "datasheet",
    "handbook",
    "meeting_note",
    "presentation",
    "manuscript",
    "abstract",
    "poster",
    "figure",
    "raw_image",
    "microscopy_image",
    "processed_image",
    "analysis_notebook",
    "code",
    "dataset",
    "spreadsheet",
    "lab_notebook",
    "project_plan",
    "project_log",
    "personnel_document",
    "administrative_document",
    "social_event_document",
    "system_artifact",
    "unknown",
)

DUPLICATE_TYPES = (
    "exact_duplicate",
    "probable_duplicate",
    "version_variant",
    "format_variant",
    "temporary_file",
    "system_artifact",
    "same_name_different_content",
    "same_content_different_name",
    "not_duplicate",
)

REVIEW_STATUSES = (
    "auto_high_confidence",
    "auto_medium_confidence",
    "needs_human_review",
    "manually_reviewed",
    "rejected",
)

# Non-project browse groups (Phase 7) — proposed clean taxonomy
NON_PROJECT_TAXONOMY: dict[str, dict[str, list[str]]] = {
    "Wet Lab Knowledge": {
        "Protocols & SOPs": ["protocol", "SOP", "instruction"],
        "Inventories & Registries": ["inventory", "registry", "spreadsheet"],
        "Assays & Platforms": [],
        "Imaging & QC": ["microscopy_image", "processed_image", "figure"],
    },
    "Orders & Procurement": {
        "Billing & Accounts": ["invoice", "order_form"],
        "Shipping & Receipts": ["shipping_document", "receipt"],
        "Vendor Records": [],
    },
    "Administration & Personnel": {
        "Onboarding & Guidelines": ["handbook", "administrative_document"],
        "Personnel": ["personnel_document"],
        "Permits & Compliance": ["permit", "safety_document", "datasheet"],
    },
    "Lab Operations": {
        "Cleaning & Maintenance": [],
        "Meeting Notes": ["meeting_note"],
    },
    "Social & Lab Memory": {
        "Events & Outreach": ["social_event_document"],
        "Photos & Media": ["raw_image", "presentation"],
    },
    "Archive": {
        "Historical Records": [],
    },
}

PROJECT_CATEGORY_NORMALIZE: dict[str, str] = {
    "writing & dissemination": "Writing & Dissemination",
    "writing and dissemination": "Writing & Dissemination",
    "writing": "Writing",
    "plan": "Plan",
    "methods": "Methods",
    "data": "Data",
    "figures": "Figures",
    "log": "Log",
    "archive": "Archive",
    "meetings": "Meetings",
    "updates": "Updates",
    "presentations": "Presentations",
    "experimenter": "Experimenter",
    "experimental": "Experimental",
    "analysis": "Analysis",
    "notebooks": "Notebooks",
}

SCIENTIFIC_PLATFORMS = (
    "xenium", "geomx", "geomet", "cycif", "tcycif", "visium", "scrna", "merfish",
    "codex", "ihc", "spatial", "multiplex",
)
