from typing import Any
from fastapi import HTTPException
from app_skeleton.security.audit_log import log_denied_access

def has_role(user: dict[str, Any], allowed_roles: list[str]) -> bool:
    """Check if the user has any of the allowed roles."""
    return user.get("role") in allowed_roles

def require_role(user: dict[str, Any], allowed_roles: list[str], resource: str = "resource") -> None:
    """Raises HTTPException if user lacks required role."""
    if not has_role(user, allowed_roles):
        log_denied_access(user.get("email", "unknown"), resource, "role_check")
        raise HTTPException(status_code=403, detail="Insufficient role permissions")

def _user_allowed_projects(user: dict[str, Any]) -> set[str] | None:
    """None means unrestricted (admin); empty set means no project access."""
    role = (user or {}).get("role") or "viewer"
    if role in {"admin", "editor"}:
        return None
    allowed = user.get("allowed_projects") or user.get("projects") or []
    if isinstance(allowed, str):
        allowed = [p.strip() for p in allowed.split(",") if p.strip()]
    return {str(p).upper() for p in allowed}


def can_read_project(user: dict[str, Any], project_id: str) -> bool:
    """Authorization logic for reading a project."""
    if not project_id:
        return True
    allowed = _user_allowed_projects(user)
    if allowed is None:
        return True
    return project_id.upper() in allowed

def can_write_project(user: dict[str, Any], project_id: str) -> bool:
    """Authorization logic for writing to a project."""
    if has_role(user, ["admin", "editor"]):
        return True
    return False

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
    if project_code and not can_read_project(user, project_code):
        return False
    role = (user or {}).get("role") or "viewer"
    path_lower = (logical_path or "").lower()
    if "/restricted/" in path_lower or "/confidential/" in path_lower:
        return role in {"admin", "editor"}
    return True
