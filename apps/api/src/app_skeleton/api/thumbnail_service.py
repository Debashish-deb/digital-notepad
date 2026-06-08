"""Lightweight preview thumbnails — local cache under DataCloud 12_APP_PREVIEWS or PREVIEW_CACHE_DIR."""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from app_skeleton.storage.env import datacloud_logical_root, pdrive_mount_path

LOGGER = logging.getLogger(__name__)

PREVIEW_FOLDER_NAME = "12_APP_PREVIEWS"
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".pdf"})
HUGE_IMAGE_BYTES = int(os.getenv("THUMBNAIL_SKIP_IMAGE_BYTES", str(50 * 1024 * 1024)))
MAX_THUMBNAILS_PER_RUN = int(os.getenv("THUMBNAIL_MAX_PER_RUN", "25"))
THUMB_MAX_EDGE = int(os.getenv("THUMBNAIL_MAX_EDGE", "256"))


def preview_cache_dir() -> Path:
    explicit = os.getenv("PREVIEW_CACHE_DIR", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    root = os.getenv("LAB_STORAGE_ROOT", "").strip()
    if root:
        return Path(root).expanduser() / PREVIEW_FOLDER_NAME
    mount = pdrive_mount_path()
    if mount:
        return Path(mount).expanduser() / PREVIEW_FOLDER_NAME
    dc = datacloud_logical_root().rstrip("/")
    safe = dc.replace("://", "_").replace("/", "_").strip("_") or "datacloud"
    return Path(tempfile.gettempdir()) / "omeia-previews" / safe / PREVIEW_FOLDER_NAME


def _thumb_key(source_path: Path) -> str:
    digest = hashlib.sha256(str(source_path.resolve()).encode("utf-8")).hexdigest()[:16]
    return f"{digest}{source_path.suffix.lower() or '.bin'}.thumb.jpg"


def _try_pillow_resize(src: Path, dest: Path) -> bool:
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        with Image.open(src) as im:
            im.thumbnail((THUMB_MAX_EDGE, THUMB_MAX_EDGE))
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            dest.parent.mkdir(parents=True, exist_ok=True)
            im.save(dest, format="JPEG", quality=82, optimize=True)
        return True
    except Exception as exc:
        LOGGER.debug("thumbnail skip %s: %s", src, exc)
        return False


def _try_pymupdf_render(src: Path, dest: Path) -> bool:
    try:
        import fitz  # type: ignore
    except ImportError:
        return False
    try:
        doc = fitz.open(str(src))
        if len(doc) == 0:
            return False
        page = doc[0]
        # Render at 72 dpi (zoom 1.0) or higher to get a decent thumbnail
        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
        dest.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(dest), "jpg")
        return True
    except Exception as exc:
        LOGGER.debug("thumbnail skip pdf %s: %s", src, exc)
        return False


def generate_thumbnail(source_path: Path, *, force: bool = False) -> dict[str, Any]:
    """Create a small JPEG preview; huge images return metadata only."""
    src = source_path.expanduser().resolve()
    if not src.is_file():
        return {"status": "missing", "source": str(src)}
    if src.suffix.lower() not in IMAGE_EXTENSIONS:
        return {"status": "skipped", "reason": "not_image", "source": str(src)}

    size = src.stat().st_size
    cache = preview_cache_dir()
    dest = cache / _thumb_key(src)
    if dest.exists() and not force:
        return {
            "status": "cached",
            "source": str(src),
            "preview_path": str(dest),
            "bytes": size,
        }

    if size > HUGE_IMAGE_BYTES:
        return {
            "status": "metadata_only",
            "reason": "image_too_large",
            "source": str(src),
            "bytes": size,
        }

    if src.suffix.lower() == ".pdf":
        if _try_pymupdf_render(src, dest):
            return {
                "status": "created",
                "source": str(src),
                "preview_path": str(dest),
                "bytes": size,
            }
    elif _try_pillow_resize(src, dest):
        return {
            "status": "created",
            "source": str(src),
            "preview_path": str(dest),
            "bytes": size,
        }

    return {
        "status": "metadata_only",
        "reason": "pillow_unavailable_or_failed",
        "source": str(src),
        "bytes": size,
    }


def scan_and_thumbnail_directory(
    root: Path,
    *,
    max_files: int | None = None,
) -> dict[str, Any]:
    """Walk root (read-only) and generate thumbnails for recent images."""
    limit = max_files if max_files is not None else MAX_THUMBNAILS_PER_RUN
    root = root.expanduser().resolve()
    if not root.is_dir():
        return {"status": "skipped", "reason": "root_missing", "root": str(root)}

    created = cached = skipped = metadata_only = 0
    examined = 0
    samples: list[dict[str, Any]] = []

    candidates: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            candidates.append(path)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for path in candidates:
        if examined >= limit:
            break
        examined += 1
        result = generate_thumbnail(path)
        status = result.get("status")
        if status == "created":
            created += 1
        elif status == "cached":
            cached += 1
        elif status == "metadata_only":
            metadata_only += 1
        else:
            skipped += 1
        if len(samples) < 5:
            samples.append({"source": result.get("source"), "status": status})

    return {
        "status": "ok",
        "root": str(root),
        "preview_cache_dir": str(preview_cache_dir()),
        "examined": examined,
        "created": created,
        "cached": cached,
        "metadata_only": metadata_only,
        "skipped": skipped,
        "samples": samples,
    }
