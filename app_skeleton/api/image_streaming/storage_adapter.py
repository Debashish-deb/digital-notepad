"""Secure image storage adapter — resolves assets without exposing paths."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, BinaryIO, Iterator

from app_skeleton.api.common import CSC_MEDIA_DIR, DATABASE_ROOT, PROJECTS_ROOT
from app_skeleton.api import document_library_service as doc_svc
from app_skeleton.api.image_streaming.constants import IMAGE_EXTENSIONS, PROVIDER_MAP

_ROOTS = {
    "database-static": DATABASE_ROOT,
    "projects-static": PROJECTS_ROOT,
    "csc-media": CSC_MEDIA_DIR,
}


def is_streamable_image(asset_row: dict[str, Any] | None) -> bool:
    if not asset_row:
        return False
    ext = (asset_row.get("extension") or "").lower()
    name = (asset_row.get("filename") or "").lower()
    if ext in IMAGE_EXTENSIONS:
        return True
    return any(name.endswith(s) for s in IMAGE_EXTENSIONS)


def _infer_provider(asset_row: dict[str, Any]) -> str:
    raw = (asset_row.get("storage_provider") or "").strip()
    if raw in PROVIDER_MAP:
        return PROVIDER_MAP[raw]
    logical = (asset_row.get("logical_path") or "").lower()
    if logical.startswith("projects/"):
        return "projects-static"
    if logical.startswith("csc-media/"):
        return "csc-media"
    return "database-static"


def lookup_asset_row(asset_id: str) -> dict[str, Any] | None:
    return doc_svc.find_row_by_asset_id(asset_id)


class ImageStorageAdapter:
    """Read-only access to image files keyed by asset_id."""

    def resolve_asset(self, asset_id: str) -> dict[str, Any] | None:
        row = lookup_asset_row(asset_id)
        if not row or not is_streamable_image(row):
            return None
        provider = _infer_provider(row)
        logical_path = row.get("logical_path") or ""
        root = _ROOTS.get(provider)
        if not root or not root.is_dir():
            return None
        disk_path = (root / logical_path).resolve()
        try:
            disk_path.relative_to(root.resolve())
        except ValueError:
            return None
        if not disk_path.is_file():
            return None
        return {
            "asset_id": asset_id,
            "provider": provider,
            "logical_path": logical_path,
            "disk_path": disk_path,
            "filename": row.get("filename"),
            "extension": row.get("extension"),
            "size_bytes": row.get("size_bytes") or disk_path.stat().st_size,
            "project_hint": row.get("project_hint"),
            "asset_row": row,
        }

    def exists(self, resolved: dict[str, Any]) -> bool:
        path = resolved.get("disk_path")
        return bool(path and Path(path).is_file())

    def get_size(self, resolved: dict[str, Any]) -> int:
        path = resolved.get("disk_path")
        if not path:
            return 0
        return Path(path).stat().st_size

    def open_read_stream(
        self,
        resolved: dict[str, Any],
        *,
        start: int | None = None,
        end: int | None = None,
    ) -> Iterator[bytes]:
        path = Path(resolved["disk_path"])
        file_size = path.stat().st_size
        byte_start = start or 0
        byte_end = end if end is not None else file_size - 1
        byte_start = max(0, byte_start)
        byte_end = min(file_size - 1, byte_end)
        if byte_start > byte_end:
            return
        chunk_size = 64 * 1024

        with path.open("rb") as fh:
            fh.seek(byte_start)
            remaining = byte_end - byte_start + 1
            while remaining > 0:
                data = fh.read(min(chunk_size, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    def read_bytes(self, resolved: dict[str, Any], *, start: int = 0, length: int | None = None) -> bytes:
        path = Path(resolved["disk_path"])
        with path.open("rb") as fh:
            fh.seek(start)
            if length is None:
                return fh.read()
            return fh.read(length)
