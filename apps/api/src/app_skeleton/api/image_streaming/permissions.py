"""Image asset access permissions."""
from __future__ import annotations

from typing import Any

from app_skeleton.security.permissions import can_access_project, can_download_file, has_role


def can_access_image_asset(user: dict[str, Any], asset_row: dict[str, Any]) -> bool:
    """Check whether user may stream/preview an image asset."""
    if not asset_row:
        return False
    logical_path = asset_row.get("logical_path") or ""
    project_code = asset_row.get("project_hint") or None
    if project_code and not can_access_project(user, project_code):
        return False
    if not can_download_file(user, logical_path, project_code=project_code):
        return False
    sensitivity = (asset_row.get("sensitivity_level") or "").lower()
    if sensitivity in {"restricted", "confidential"}:
        return has_role(user, ["admin", "editor"])
    return True


def require_admin(user: dict[str, Any]) -> bool:
    return has_role(user, ["admin"])
