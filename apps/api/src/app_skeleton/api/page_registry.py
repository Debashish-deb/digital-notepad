"""Page domain registry — maps corpus sections to IA (LUMI-W001)."""
from __future__ import annotations

import os
from typing import Any

import psycopg

_SECTION_HINT_TO_PAGE: dict[str, tuple[str, str | None]] = {
    "overview_onboarding": ("overview", "overview.onboarding"),
    "overview_guidelines": ("overview", "overview.guidelines"),
    "overview_documents": ("overview", "overview.documents"),
    "overview_personnel": ("overview", "overview.personnel"),
    "overview_cleaning": ("overview", "overview.cleaning"),
    "overview_general": ("overview", "overview.get_started"),
    "overview_get_started": ("overview", "overview.get_started"),
    "overview_research_materials": ("research_hub", "research.materials"),
    "orders_billing": ("orders", "orders.billing"),
    "orders_archive": ("orders", "orders.archive"),
    "social_misc": ("overview", "overview.social"),
    "wet_lab_files": ("wet_lab", "wet.files"),
}

_DOMAIN_TO_PAGE: dict[str, str] = {
    "project": "projects",
    "lab_operations": "wet_lab",
    "administration": "overview",
    "orders_procurement": "orders",
    "social_memory": "social",
    "unknown": "knowledge_base",
}


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


def resolve_page_ids(
    *,
    domain: str | None,
    section_hint: str | None,
    logical_path: str | None = None,
) -> tuple[str | None, str | None]:
    hint = (section_hint or "").strip()
    if hint in _SECTION_HINT_TO_PAGE:
        return _SECTION_HINT_TO_PAGE[hint]
    dom = (domain or "").strip()
    if dom == "project":
        return "projects", "projects.files"
    page_domain = _DOMAIN_TO_PAGE.get(dom, "knowledge_base")
    return page_domain, None


def list_domains() -> list[dict[str, Any]]:
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT d.page_domain_id, d.label, d.description,
                           COUNT(s.page_section_id) AS section_count
                    FROM platform.page_domain d
                    LEFT JOIN platform.page_section s ON s.page_domain_id = d.page_domain_id
                    GROUP BY d.page_domain_id, d.label, d.description
                    ORDER BY d.sort_order;
                    """
                )
                return [
                    {
                        "page_domain_id": r[0],
                        "label": r[1],
                        "description": r[2],
                        "section_count": r[3],
                    }
                    for r in cur.fetchall()
                ]
    except Exception:
        return []


def list_sections(page_domain_id: str | None = None) -> list[dict[str, Any]]:
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                if page_domain_id:
                    cur.execute(
                        """
                        SELECT page_section_id, page_domain_id, label, nav_screen,
                               database_section_id, description
                        FROM platform.page_section
                        WHERE page_domain_id = %s
                        ORDER BY sort_order;
                        """,
                        (page_domain_id,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT page_section_id, page_domain_id, label, nav_screen,
                               database_section_id, description
                        FROM platform.page_section
                        ORDER BY page_domain_id, sort_order;
                        """
                    )
                return [
                    {
                        "page_section_id": r[0],
                        "page_domain_id": r[1],
                        "label": r[2],
                        "nav_screen": r[3],
                        "database_section_id": r[4],
                        "description": r[5],
                    }
                    for r in cur.fetchall()
                ]
    except Exception:
        return []
