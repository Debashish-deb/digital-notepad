"""Serve Vite production build from FastAPI when OMEIA_FRONTEND_MODE=prod."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from omeia.api.paths import REPO_ROOT

LOGGER = logging.getLogger(__name__)

_RESERVED_PREFIXES = (
    "/api/",
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/database-static/",
    "/projects-static/",
    "/stats",
)


def frontend_mode() -> str:
    return (os.getenv("OMEIA_FRONTEND_MODE", "dev") or "dev").strip().lower()


def should_serve_frontend_static() -> bool:
    if frontend_mode() != "prod":
        return False
    return (os.getenv("OMEIA_SERVE_FRONTEND_STATIC", "true") or "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def frontend_dist_dir() -> Path:
    return REPO_ROOT / "omeia" / "ui" / "react_frontend" / "dist"


def register_frontend_static(app: FastAPI) -> bool:
    """Mount dist/ assets and SPA fallback. Call after all API routers."""
    if not should_serve_frontend_static():
        return False

    dist = frontend_dist_dir()
    if not dist.is_dir():
        LOGGER.warning("OMEIA_FRONTEND_MODE=prod but %s missing — skipping static mount", dist)
        return False

    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("assets/"):
            raise HTTPException(status_code=404, detail="Asset not found")
        for prefix in _RESERVED_PREFIXES:
            key = prefix.rstrip("/")
            if full_path == key or full_path.startswith(prefix):
                raise HTTPException(status_code=404, detail="Not found")
        candidate = (dist / full_path).resolve()
        try:
            candidate.relative_to(dist.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="Invalid path") from exc
        if candidate.is_file():
            return FileResponse(candidate)
        index = dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Frontend build missing index.html")

    LOGGER.info("Serving frontend static build from %s", dist)
    return True
