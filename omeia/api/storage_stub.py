"""Portable storage backend — local/stub now; remote mounts later without code changes."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import psycopg

from omeia.api.paths import DATABASE_ROOT, PROCESSED_DIR, PROJECTS_ROOT
from omeia.api.qdrant_vectors import get_qdrant_client, ping_qdrant
from omeia.api.supabase_config import postgres_conn

LOGGER = logging.getLogger(__name__)

# stub  = repo-relative DATABASE_ROOT + processed JSON (default, git-portable)
# local = explicit DATABASE_ROOT on workstation
# remote = future SMB/DataCloud mounts (same APIs, different roots via env)
STORAGE_MODE = os.getenv("OMEIA_STORAGE_MODE", "stub").strip().lower() or "stub"


def ping_postgres(conn: str | None = None) -> bool:
    dsn = conn or postgres_conn()
    try:
        with psycopg.connect(dsn, connect_timeout=4) as conn_obj:
            with conn_obj.cursor() as cur:
                cur.execute("SELECT 1;")
        return True
    except Exception as exc:
        LOGGER.debug("Postgres ping failed: %s", exc)
        return False


def storage_roots() -> dict[str, Any]:
    """Safe status for APIs — no absolute server paths in user-facing fields."""
    db_exists = DATABASE_ROOT.is_dir()
    projects_exists = PROJECTS_ROOT.is_dir()
    processed_exists = PROCESSED_DIR.is_dir()
    from omeia.api.data_layout import iter_lab_processed_files

    lab_sections = len(list(iter_lab_processed_files())) if processed_exists else 0
    project_twins = len([
        p for p in PROCESSED_DIR.glob("*.json")
        if not p.name.startswith("lab__")
    ]) if processed_exists else 0

    return {
        "mode": STORAGE_MODE,
        "database_available": db_exists,
        "projects_available": projects_exists,
        "processed_index_available": processed_exists,
        "lab_section_twins": lab_sections,
        "project_twins": max(0, project_twins),
        "postgres_online": ping_postgres(),
        "qdrant_online": ping_qdrant(get_qdrant_client()),
    }


def resolve_data_root_hint() -> str:
    """Relative hint only — for docs/debug, not for file serving."""
    if STORAGE_MODE == "remote":
        return "remote_mount"
    try:
        return DATABASE_ROOT.name or "database"
    except Exception:
        return "database"
