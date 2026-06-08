"""TIFF/OME-TIFF header inspection — no full image load."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from omeia.api.paths import BLUEPRINT_ROOT
from omeia.api.image_streaming.constants import (
    IMAGE_EXTENSIONS,
    METADATA_ONLY_BYTES,
    OME_TIFF_SUFFIXES,
)

LOGGER = logging.getLogger(__name__)

CACHE_PATH = BLUEPRINT_ROOT / "omeia" / "data" / "image_metadata_cache.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_cache() -> dict[str, Any]:
    if not CACHE_PATH.is_file():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        LOGGER.warning("image metadata cache read failed: %s", exc)
        return {}


def _save_cache(data: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_cached_metadata(asset_id: str) -> dict[str, Any] | None:
    entry = _load_cache().get(asset_id)
    if not entry:
        return None
    return entry.get("image") or entry


def set_cached_metadata(asset_id: str, image_meta: dict[str, Any]) -> dict[str, Any]:
    cache = _load_cache()
    cache[asset_id] = {
        "asset_id": asset_id,
        "updated_at": _utc_now(),
        "image": image_meta,
    }
    _save_cache(cache)
    return image_meta


def detect_image_kind(filename: str, extension: str) -> str:
    name = (filename or "").lower()
    ext = (extension or "").lower()
    if any(name.endswith(s) for s in OME_TIFF_SUFFIXES):
        return "ome_tiff"
    if ext in {".tif", ".tiff"} or name.endswith((".tif", ".tiff")):
        return "tiff"
    return "unsupported"


class ImageMetadataService:
    """Extract streaming-oriented metadata from TIFF headers."""

    def build_stub(self, *, asset_id: str, filename: str, extension: str, size_bytes: int) -> dict[str, Any]:
        kind = detect_image_kind(filename, extension)
        status = "metadata_only" if size_bytes >= METADATA_ONLY_BYTES else "unknown"
        return {
            "asset_id": asset_id,
            "format": kind,
            "streaming_status": status,
            "size_bytes": size_bytes,
            "inspected_at": None,
            "dimensions": None,
            "channels": None,
            "dtype": None,
            "pyramid_levels": 0,
            "series_count": 0,
            "ome_xml_present": False,
            "tile_ready": False,
            "thumbnail_ready": False,
            "errors": [],
        }

    def inspect_file(
        self,
        disk_path: Path,
        *,
        asset_id: str,
        filename: str,
        extension: str,
        size_bytes: int,
    ) -> dict[str, Any]:
        meta = self.build_stub(
            asset_id=asset_id,
            filename=filename,
            extension=extension,
            size_bytes=size_bytes,
        )
        try:
            import tifffile  # type: ignore
        except ImportError:
            meta["streaming_status"] = "metadata_only"
            meta["errors"].append("tifffile_not_installed")
            return set_cached_metadata(asset_id, meta)

        try:
            with tifffile.TiffFile(str(disk_path)) as tif:
                meta["ome_xml_present"] = bool(getattr(tif, "ome_metadata", None))
                meta["series_count"] = len(tif.series)
                series = tif.series[0] if tif.series else None
                if series is not None:
                    shape = list(series.shape)
                    meta["dimensions"] = {
                        "shape": shape,
                        "axes": getattr(series, "axes", "") or "",
                    }
                    if len(shape) >= 2:
                        meta["height"] = shape[-2]
                        meta["width"] = shape[-1]
                    if "C" in (getattr(series, "axes", "") or ""):
                        meta["channels"] = shape[(series.axes or "").index("C")]
                    elif len(shape) >= 3:
                        meta["channels"] = shape[0] if len(shape) == 3 else None
                pages = tif.pages
                meta["page_count"] = len(pages)
                levels = 1
                if pages:
                    first = pages[0]
                    if first.subifds:
                        levels = 1 + len(first.subifds)
                meta["pyramid_levels"] = levels
                meta["pyramidal"] = levels > 1
                if pages:
                    meta["dtype"] = str(pages[0].dtype)
                meta["tile_ready"] = True
                meta["streaming_status"] = "tile_ready"
                meta["inspected_at"] = _utc_now()
        except Exception as exc:
            LOGGER.debug("TIFF inspect failed for %s: %s", asset_id, exc)
            meta["streaming_status"] = "failed"
            meta["errors"].append(str(exc))

        return set_cached_metadata(asset_id, meta)

    def get_or_stub(
        self,
        *,
        asset_id: str,
        filename: str,
        extension: str,
        size_bytes: int,
    ) -> dict[str, Any]:
        cached = get_cached_metadata(asset_id)
        if cached:
            return cached
        stub = self.build_stub(
            asset_id=asset_id,
            filename=filename,
            extension=extension,
            size_bytes=size_bytes,
        )
        return stub
