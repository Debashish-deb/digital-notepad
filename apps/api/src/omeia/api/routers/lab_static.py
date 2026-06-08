"""Serve lab/project media for dev previews — mirrors Vite databaseStaticPlugin.

Used when Vite proxies /database-static and /projects-static to the API (LAN/Tailscale access).
"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from omeia.api.paths import DATABASE_ROOT, PROJECTS_ROOT
from omeia.api.platform_flags import require_auth_static_enabled
from omeia.security.auth import require_platform_user

router = APIRouter(tags=["lab-static"])


async def _static_auth_guard(request: Request) -> dict[str, Any] | None:
    if not require_auth_static_enabled():
        return None
    return await require_platform_user(request)


def _resolve_under_root(root: Path, rel: str) -> Path:
    rel = (rel or "").lstrip("/").replace("\\", "/")
    if not rel or rel.startswith("..") or "/.." in rel:
        raise HTTPException(status_code=400, detail="Invalid path")
    if not root.is_dir():
        raise HTTPException(status_code=404, detail="Storage root not configured")
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Path escapes allowed root") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return candidate


def _file_response(path: Path) -> FileResponse:
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path=path, media_type=media_type, content_disposition_type="inline")


@router.get("/database-static/{file_path:path}")
async def serve_database_static(
    file_path: str,
    _user: dict[str, Any] | None = Depends(_static_auth_guard),
) -> FileResponse:
    return _file_response(_resolve_under_root(DATABASE_ROOT, file_path))


@router.get("/projects-static/{file_path:path}")
async def serve_projects_static(
    file_path: str,
    _user: dict[str, Any] | None = Depends(_static_auth_guard),
) -> FileResponse:
    return _file_response(_resolve_under_root(PROJECTS_ROOT, file_path))
