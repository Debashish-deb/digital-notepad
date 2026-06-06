import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from typing import Any

from app_skeleton.api.common import CSC_MEDIA_DIR, PROJECTS_ROOT, DATABASE_ROOT
from app_skeleton.security.auth import require_platform_user
from app_skeleton.security.permissions import can_download_file
from app_skeleton.security.audit_log import log_file_download

router = APIRouter(
    prefix="/api/files",
    tags=["secure-files"],
    dependencies=[Depends(require_platform_user)]
)

ALLOWED_ROOTS = {
    "csc-media": CSC_MEDIA_DIR,
    "projects-static": PROJECTS_ROOT,
    "database-static": DATABASE_ROOT
}

def _resolve_secure_path(provider: str, logical_path: str) -> Path:
    """
    Safely resolves a logical path against a known provider root.
    Blocks path traversal and absolute paths.
    """
    if provider not in ALLOWED_ROOTS:
        raise HTTPException(status_code=400, detail="Invalid file provider")
        
    root_path = ALLOWED_ROOTS[provider]
    if not root_path.exists():
        raise HTTPException(status_code=404, detail="Provider not found")
        
    # Prevent absolute paths
    if logical_path.startswith("/") or logical_path.startswith("\\"):
        raise HTTPException(status_code=400, detail="Absolute paths not allowed")
        
    # Prevent directory traversal
    if ".." in logical_path:
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
        
    resolved_path = (root_path / logical_path).resolve()
    resolved_root = root_path.resolve()
    
    # Final check: Ensure the resolved path actually stays within the allowed root
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Path escapes allowed root")
        
    return resolved_path

@router.get("/download")
async def download_file(
    provider: str = Query(..., description="The storage provider, e.g., 'projects-static'"),
    logical_path: str = Query(..., description="The path relative to the provider root"),
    user: dict[str, Any] = Depends(require_platform_user)
):
    """Securely download a file."""
    if not can_download_file(user, logical_path):
        raise HTTPException(status_code=403, detail="Not authorized to download this file")
        
    file_path = _resolve_secure_path(provider, logical_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    log_file_download(user.get("email", "unknown"), f"{provider}/{logical_path}")
    return FileResponse(path=file_path, filename=file_path.name)

@router.get("/preview")
async def preview_file(
    provider: str = Query(..., description="The storage provider"),
    logical_path: str = Query(..., description="The path relative to the provider root"),
    user: dict[str, Any] = Depends(require_platform_user)
):
    """Securely preview a file inline."""
    if not can_download_file(user, logical_path):
        raise HTTPException(status_code=403, detail="Not authorized to preview this file")
        
    file_path = _resolve_secure_path(provider, logical_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(path=file_path, filename=file_path.name, content_disposition_type="inline")

@router.get("/metadata")
async def file_metadata(
    provider: str = Query(..., description="The storage provider"),
    logical_path: str = Query(..., description="The path relative to the provider root"),
    user: dict[str, Any] = Depends(require_platform_user)
):
    """Securely get file metadata without downloading."""
    if not can_download_file(user, logical_path):
        raise HTTPException(status_code=403, detail="Not authorized to view metadata")
        
    file_path = _resolve_secure_path(provider, logical_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    stat = file_path.stat()
    return {
        "filename": file_path.name,
        "size_bytes": stat.st_size,
        "created_at": stat.st_ctime,
        "modified_at": stat.st_mtime,
    }
