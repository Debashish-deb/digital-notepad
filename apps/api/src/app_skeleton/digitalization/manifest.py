"""Manifest scanner — discovery phase only, no extraction."""
from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app_skeleton.digitalization.models import SourceFileManifest
from app_skeleton.digitalization.status import Status

LOGGER = logging.getLogger(__name__)

SKIP_PARTS = {
    ".git", "node_modules", ".venv", "__pycache__", ".DS_Store",
    ".dart_tool", "build", "dist", ".next", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "coverage", "12_APP_PREVIEWS",
}

SUPPORTED_EXTENSIONS = frozenset({
    ".txt", ".md", ".csv", ".tsv", ".json", ".jsonl",
    ".yaml", ".yml", ".toml", ".xml", ".html", ".htm",
    ".pdf", ".docx", ".doc", ".dotx", ".odt", ".rtf",
    ".pptx", ".ppt", ".odp",
    ".xlsx", ".xls", ".ods",
    ".py", ".r", ".sh", ".sql",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".bmp", ".svg",
})


def _sha256_file(path: Path, limit_bytes: int = 64 * 1024 * 1024) -> str | None:
    """Compute SHA-256 of a file, reading up to limit_bytes."""
    try:
        h = hashlib.sha256()
        read = 0
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(1024 * 1024), b""):
                if read + len(block) > limit_bytes:
                    block = block[: max(0, limit_bytes - read)]
                if not block:
                    break
                h.update(block)
                read += len(block)
                if read >= limit_bytes:
                    break
        return h.hexdigest()
    except OSError:
        return None


def _utc_iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, timezone.utc).isoformat()
    except Exception:
        return None


def scan_local_directory(
    root: Path,
    *,
    max_files: int | None = None,
    provider: str = "local",
) -> list[SourceFileManifest]:
    """Walk a directory tree and produce manifest entries (discovery only)."""
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Scan root not found: {root}")

    results: list[SourceFileManifest] = []
    count = 0

    for path in sorted(root.rglob("*")):
        if max_files is not None and count >= max_files:
            break
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue

        ext = path.suffix.lower()
        try:
            rel = str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            continue

        try:
            stat = path.stat()
            size = int(stat.st_size)
            mtime = stat.st_mtime
        except OSError:
            size = 0
            mtime = None

        status = Status.DISCOVERED
        if ext not in SUPPORTED_EXTENSIONS:
            status = Status.SKIPPED_UNSUPPORTED

        checksum = _sha256_file(path) if size < 100 * 1024 * 1024 else None

        results.append(SourceFileManifest(
            provider=provider,
            logical_path=rel,
            file_name=path.name,
            file_ext=ext,
            size_bytes=size,
            modified_at=_utc_iso(mtime),
            checksum_sha256=checksum,
            status=status,
            metadata={
                "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            },
        ))
        count += 1

    return results
