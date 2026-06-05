"""Central path configuration with environment overrides and safe helpers."""
from __future__ import annotations

import os
from pathlib import Path

from app_skeleton.storage.env import (
    CANONICAL_DATACLOUD_ROOT,
    datacloud_webdav_base_url,
    pdrive_enabled,
    pdrive_mount_path,
)

# Platform application root (repository root after flatten)
BLUEPRINT_ROOT = Path(__file__).resolve().parents[2]

# Same as BLUEPRINT_ROOT unless OMEIA_REPO_ROOT is set explicitly
REPO_ROOT = Path(os.environ.get("OMEIA_REPO_ROOT", str(BLUEPRINT_ROOT))).expanduser().resolve()


def _default_database_root() -> Path:
    explicit = os.environ.get("DATABASE_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    external = (BLUEPRINT_ROOT.parent / "OMEIA-database").expanduser().resolve()
    if external.is_dir():
        return external
    legacy = REPO_ROOT / "database"
    return legacy.expanduser().resolve()


def _default_projects_root() -> Path:
    database_root = _default_database_root()
    database_projects = database_root / "projects"
    if database_projects.is_dir():
        return database_projects
    legacy = REPO_ROOT / "projects"
    return legacy if legacy.is_dir() else database_projects


PROJECTS_ROOT = Path(os.environ.get("PROJECTS_ROOT", str(_default_projects_root()))).expanduser().resolve()
DATABASE_ROOT = _default_database_root()

_LAB_STORAGE_RAW = os.environ.get("LAB_STORAGE_ROOT", "").strip()


def lab_storage_root() -> Path | None:
    """Mounted SMB or explicit lab notebook root — never hardcoded."""
    if not _LAB_STORAGE_RAW:
        return None
    p = Path(_LAB_STORAGE_RAW).expanduser()
    return p.resolve() if p.is_dir() else None


def projects_roots_for_scan() -> list[Path]:
    """Ordered scan roots: LAB_STORAGE_ROOT, then PROJECTS_ROOT."""
    roots: list[Path] = []
    lr = lab_storage_root()
    if lr:
        roots.append(lr)
    if PROJECTS_ROOT.is_dir() and (not lr or PROJECTS_ROOT.resolve() != lr):
        roots.append(PROJECTS_ROOT)
    return roots
CATALOG_PATH = Path(os.environ.get(
    "PROJECTS_CATALOG_PATH",
    str(BLUEPRINT_ROOT / "app_skeleton" / "data" / "projects_catalog.json"),
)).expanduser().resolve()
PROCESSED_DIR = Path(os.environ.get(
    "PROCESSED_PROJECTS_DIR",
    str(BLUEPRINT_ROOT / "app_skeleton" / "data" / "processed_projects"),
)).expanduser().resolve()
PUBLIC_PROCESSED_DIR = Path(os.environ.get(
    "PUBLIC_PROCESSED_DIR",
    str(BLUEPRINT_ROOT / "app_skeleton" / "ui" / "react_frontend" / "public" / "processed"),
)).expanduser().resolve()
SCRIPTS_DIR = Path(os.environ.get("PLATFORM_SCRIPTS_DIR", str(BLUEPRINT_ROOT / "scripts"))).expanduser().resolve()
CSC_MEDIA_DIR = Path(os.environ.get("CSC_MEDIA_DIR", str(REPO_ROOT / "CSC"))).expanduser().resolve()

# Phase 1 — storage roots (server-side only; never expose raw connector paths to the frontend).
_SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
_SUPABASE_STORAGE = bool(
    _SUPABASE_URL
    and (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.environ.get("SERVICE_ROLE_KEY", "").strip()
    )
)

STORAGE_PROVIDERS: tuple[dict[str, str], ...] = (
    {
        "id": "datacloud_webdav",
        "role": "primary_research",
        "description": "University of Helsinki DataCloud WebDAV (canonical originals)",
    },
    {
        "id": "pdrive_smb",
        "role": "secondary_research",
        "description": "P-drive SMB shared lab storage (mounted path)",
    },
    {
        "id": "supabase_storage",
        "role": "small_files_previews",
        "description": "Supabase Storage for avatars, UI assets, small previews only",
    },
    {
        "id": "supabase_postgres",
        "role": "metadata_permissions_vectors",
        "description": "PostgreSQL metadata, permissions, and vector indexes",
    },
    {
        "id": "local_database_mirror",
        "role": "evidence_mirror",
        "description": "Local evidence mirror under DATABASE_ROOT (dev/onboarding)",
    },
)


def storage_roots_public_summary() -> list[dict[str, str | bool | None]]:
    """Provider registry for ops dashboards — no host paths or credentials."""
    configured = {
        "datacloud_webdav": bool(datacloud_webdav_base_url()),
        "pdrive_smb": pdrive_enabled() and bool(pdrive_mount_path()),
        "supabase_storage": _SUPABASE_STORAGE,
        "supabase_postgres": bool(
            _SUPABASE_URL
            and (
                os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
                or os.environ.get("SERVICE_ROLE_KEY", "").strip()
            )
        )
        or bool(os.environ.get("SUPABASE_DB_PASSWORD", "").strip())
        or bool(os.environ.get("POSTGRES_CONN", "").strip()),
        "local_database_mirror": DATABASE_ROOT.is_dir(),
    }
    try:
        import psycopg
        from app_skeleton.api.supabase_config import postgres_conn

        conn_str = postgres_conn()
        if conn_str:
            with psycopg.connect(conn_str, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT storage_root_id, provider_id, role, root_logical_path, configured, description
                        FROM platform.storage_root
                        WHERE provider_id <> 'cloudflare_r2'
                        ORDER BY storage_root_id;
                        """
                    )
                    rows = cur.fetchall()
                    if rows:
                        return [
                            {
                                "id": r[0],
                                "provider_id": r[1],
                                "role": r[2],
                                "root_logical_path": r[3],
                                "configured": bool(r[4]),
                                "description": r[5],
                            }
                            for r in rows
                        ]
    except Exception:
        pass
    return [
        {
            **meta,
            "configured": configured.get(meta["id"], False),
            "root_logical_path": CANONICAL_DATACLOUD_ROOT if meta["id"] == "datacloud_webdav" else None,
        }
        for meta in STORAGE_PROVIDERS
    ]


CHECKER_SCRIPTS: dict[str, str] = {
    "python_env": "check_python_env.sh",
    "gpu": "check_gpu.sh",
    "napari": "check_napari.sh",
    "docker": "check_docker.sh",
    "lumi_modules": "check_lumi_modules.sh",
    "cylinter_inputs": "check_cylinter_inputs.py",
    "project_structure": "check_tcycif_project_structure.py",
}


def ensure_runtime_dirs() -> None:
    """Create writable runtime data directories if they do not already exist."""
    for path in (PROCESSED_DIR, PUBLIC_PROCESSED_DIR):
        path.mkdir(parents=True, exist_ok=True)


def safe_relative_path(root: Path, relative_path: str) -> Path:
    """Resolve a user-supplied relative path under *root* or raise ValueError.

    This prevents path traversal and sibling-prefix bypasses such as
    `/project` vs `/project-old`.
    """
    root = root.expanduser().resolve()
    candidate = (root / relative_path).expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Path escapes configured root") from exc
    return candidate


def checker_script(name: str) -> Path | None:
    filename = CHECKER_SCRIPTS.get((name or "").strip())
    if not filename:
        return None
    path = (SCRIPTS_DIR / filename).resolve()
    try:
        path.relative_to(SCRIPTS_DIR)
    except ValueError:
        return None
    return path if path.exists() and path.is_file() else None
