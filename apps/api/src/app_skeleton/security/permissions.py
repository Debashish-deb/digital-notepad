from __future__ import annotations

from typing import Any

import psycopg
from fastapi import HTTPException

from app_skeleton.api.platform_flags import project_rbac_enabled
from app_skeleton.security.audit_log import log_denied_access


def has_role(user: dict[str, Any], allowed_roles: list[str]) -> bool:
    """Check if the user has any of the allowed roles."""
    return user.get("role") in allowed_roles


def require_role(user: dict[str, Any], allowed_roles: list[str], resource: str = "resource") -> None:
    """Raises HTTPException if user lacks required role."""
    if not has_role(user, allowed_roles):
        log_denied_access(user.get("email", "unknown"), resource, "role_check")
        raise HTTPException(status_code=403, detail="Insufficient role permissions")


def ensure_authenticated_for_rbac(user: dict[str, Any] | None) -> dict[str, Any]:
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required when PROJECT_RBAC_ENABLED=true",
        )
    return user


def _user_allowed_projects(user: dict[str, Any]) -> set[str] | None:
    """None means unrestricted (admin); empty set means no project access."""
    role = (user or {}).get("role") or "viewer"
    if role in {"admin", "editor"}:
        return None
    allowed = user.get("allowed_projects") or user.get("projects") or []
    if isinstance(allowed, str):
        allowed = [p.strip() for p in allowed.split(",") if p.strip()]
    return {str(p).upper() for p in allowed}


def _project_codes_for_researcher(cur: Any, researcher_id: Any) -> set[str]:
    codes: set[str] = set()
    cur.execute(
        """
        SELECT upper(p.project_code)
        FROM platform.project_member pm
        JOIN core.project p ON p.project_id = pm.project_id
        WHERE pm.researcher_id = %s;
        """,
        (researcher_id,),
    )
    codes.update(row[0] for row in cur.fetchall() if row and row[0])

    cur.execute(
        "SELECT allowed_project_codes FROM platform.researcher WHERE researcher_id = %s;",
        (researcher_id,),
    )
    row = cur.fetchone()
    if row and row[0]:
        codes.update(str(c).upper() for c in row[0] if c)
    return codes


def project_codes_for_user(cur: Any, user: dict[str, Any]) -> set[str] | None:
    """Return accessible project codes; None means unrestricted (platform admin)."""
    if has_role(user, ["admin"]):
        return None
    from app_skeleton.security.auth import resolve_researcher_id

    researcher_id = resolve_researcher_id(cur, user)
    return _project_codes_for_researcher(cur, researcher_id)


def can_access_project(
    user: dict[str, Any],
    project_code: str,
    *,
    cur: Any | None = None,
) -> bool:
    """Project-level access check; no-op when PROJECT_RBAC_ENABLED=false."""
    if not project_rbac_enabled():
        return True
    if not project_code:
        return True
    if has_role(user, ["admin"]):
        return True

    code = project_code.strip().upper()
    if cur is not None:
        allowed = project_codes_for_user(cur, user)
        if allowed is None:
            return True
        return code in allowed

    from app_skeleton.api.supabase_config import postgres_conn

    conn_str = postgres_conn().strip()
    if not conn_str:
        legacy = _user_allowed_projects(user)
        return legacy is None or code in legacy

    with psycopg.connect(conn_str, connect_timeout=5) as conn:
        with conn.cursor() as inner:
            allowed = project_codes_for_user(inner, user)
            if allowed is None:
                return True
            return code in allowed


def ensure_project_access(
    user: dict[str, Any],
    project_code: str,
    *,
    cur: Any | None = None,
    resource: str = "project",
) -> None:
    if not can_access_project(user, project_code, cur=cur):
        log_denied_access(user.get("email", "unknown"), f"{resource}:{project_code}", "project_rbac")
        raise HTTPException(status_code=403, detail=f"Access denied for project {project_code}")


def filter_projects_for_user(
    user: dict[str, Any],
    projects: list[dict[str, Any]],
    cur: Any,
) -> list[dict[str, Any]]:
    allowed = project_codes_for_user(cur, user)
    if allowed is None:
        return projects
    return [
        p for p in projects
        if (p.get("project_code") or "").strip().upper() in allowed
    ]


def can_read_project(user: dict[str, Any], project_id: str) -> bool:
    """Authorization logic for reading a project."""
    if not project_rbac_enabled():
        if not project_id:
            return True
        allowed = _user_allowed_projects(user)
        if allowed is None:
            return True
        return project_id.upper() in allowed
    return can_access_project(user, project_id)


def can_write_project(user: dict[str, Any], project_id: str) -> bool:
    """Authorization logic for writing to a project."""
    if not project_rbac_enabled():
        if has_role(user, ["admin", "editor"]):
            return True
        return False
    if has_role(user, ["admin"]):
        return True
    return can_access_project(user, project_id)


def can_delete_project(user: dict[str, Any], project_id: str) -> bool:
    """Authorization logic for deleting a project."""
    if has_role(user, ["admin"]):
        return True
    return False


def can_read_document(user: dict[str, Any], document_id: str, *, visibility: str | None = None) -> bool:
    """Authorization logic for reading a document."""
    role = (user or {}).get("role") or "viewer"
    if role == "admin":
        return True
    level = (visibility or "lab").lower()
    if level in {"restricted", "confidential"}:
        return role in {"admin", "editor"}
    return True


def can_download_file(user: dict[str, Any], logical_path: str, *, project_code: str | None = None) -> bool:
    """Authorization logic for downloading a file."""
    if project_code and not can_access_project(user, project_code):
        return False
    role = (user or {}).get("role") or "viewer"
    path_lower = (logical_path or "").lower()
    if "/restricted/" in path_lower or "/confidential/" in path_lower:
        return role in {"admin", "editor"}
    return True
