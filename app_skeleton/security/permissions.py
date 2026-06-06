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

def can_read_project(user: dict[str, Any], project_id: str) -> bool:
    """Authorization logic for reading a project."""
    # Expand with specific database checks if needed
    return True

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

def can_read_document(user: dict[str, Any], document_id: str) -> bool:
    """Authorization logic for reading a document."""
    return True

def can_download_file(user: dict[str, Any], logical_path: str) -> bool:
    """Authorization logic for downloading a file."""
    # Ensure they have access to the file's project/area
    return True
