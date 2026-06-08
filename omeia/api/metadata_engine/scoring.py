"""Metadata completeness scoring."""
from __future__ import annotations

from typing import Any


def metadata_score(record: dict[str, Any]) -> tuple[int, list[str]]:
    """Return (score 0-100, missing_fields)."""
    sm = record.get("suggested_metadata") or record
    missing: list[str] = []
    points = 0
    max_points = 100

    checks: list[tuple[str, bool, int]] = [
        ("display_title", bool(sm.get("display_title")), 12),
        ("detected_file_type", bool(sm.get("detected_file_type") and sm.get("detected_file_type") != "unknown"), 8),
        ("document_role", bool(sm.get("document_role") and sm.get("document_role") != "unknown"), 10),
        ("category", bool(sm.get("current_category") or sm.get("cleaned_category")), 10),
        ("extraction_status", bool(sm.get("extraction_status")), 8),
        ("preview_status", bool(sm.get("preview_status")), 6),
        ("search_aliases", len(sm.get("search_aliases") or []) >= 2, 6),
        ("duplicate_status", bool(sm.get("duplicate_status")), 6),
        ("confidence_score", sm.get("confidence_score") is not None, 6),
        ("review_status", bool(sm.get("review_status")), 6),
        ("indexed_in_search", sm.get("has_embedding") or sm.get("has_text"), 10),
        ("scientific_metadata", bool(
            sm.get("assay") or sm.get("platform") or sm.get("sample_id") or sm.get("marker_terms")
        ), 8),
        ("project_metadata", (
            not sm.get("is_project_file")
            or (sm.get("project_id") and sm.get("project_category_original"))
        ), 10),
        ("subtitle_or_context", bool(sm.get("subtitle") or sm.get("project_name")), 4),
    ]

    for field, ok, weight in checks:
        if ok:
            points += weight
        else:
            missing.append(field)

    score = int(round(100 * points / max_points))
    return min(100, score), missing


def metadata_grade(score: int) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 55:
        return "usable"
    if score >= 40:
        return "weak"
    return "poor"
