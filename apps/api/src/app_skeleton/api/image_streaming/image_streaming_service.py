"""Image streaming orchestration — manifest, tiles, thumbnails, byte streams."""
from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app_skeleton.api.image_streaming.constants import (
    DEFAULT_THUMB_EDGE,
    MAX_TILE_EDGE,
    MAX_TILE_PIXELS,
)
from app_skeleton.api.image_streaming.image_metadata_service import (
    ImageMetadataService,
    get_cached_metadata,
    set_cached_metadata,
)
from app_skeleton.api.image_streaming.job_queue import ImageJobQueue
from app_skeleton.api.image_streaming.storage_adapter import ImageStorageAdapter, lookup_asset_row
from app_skeleton.api.thumbnail_service import preview_cache_dir

LOGGER = logging.getLogger(__name__)


def _image_plane_shape(shape: tuple[int, ...]) -> tuple[int, int]:
    if len(shape) < 2:
        return 1, 1
    return int(shape[-2]), int(shape[-1])


def _get_pyramid_page(tif: Any, *, series: int, level: int) -> Any:
    """Resolve TIFF page for series and pyramid level (SubIFD chain)."""
    if tif.series and series < len(tif.series):
        pages = tif.series[series].pages
        page = pages[0] if pages else tif.pages[0]
    else:
        page = tif.pages[0]
    if level > 0 and page.subifds and level - 1 < len(page.subifds):
        page = page.subifds[level - 1]
    return page


def _build_tile_key(
    shape: tuple[int, ...],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    channel: int,
    z: int,
    t: int,
) -> tuple:
    y_end = y + height
    x_end = x + width
    if len(shape) == 2:
        return (slice(y, y_end), slice(x, x_end))
    if len(shape) == 3:
        if shape[0] <= 8:
            ch = min(channel, shape[0] - 1)
            return (ch, slice(y, y_end), slice(x, x_end))
        ch = min(channel, shape[2] - 1)
        return (slice(y, y_end), slice(x, x_end), ch)
    if len(shape) == 4:
        ti = min(t, shape[0] - 1)
        ch = min(channel, shape[1] - 1)
        return (ti, ch, slice(y, y_end), slice(x, x_end))
    ti = min(t, shape[0] - 1)
    zi = min(z, shape[1] - 1)
    ch = min(channel, shape[2] - 1)
    return (ti, zi, ch, slice(y, y_end), slice(x, x_end))


def _read_tile_region(
    page: Any,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    channel: int,
    z: int,
    t: int,
) -> Any:
    import numpy as np  # type: ignore

    shape = tuple(int(s) for s in page.shape)
    img_h, img_w = _image_plane_shape(shape)
    if x >= img_w or y >= img_h:
        raise HTTPException(status_code=400, detail="Tile origin outside image bounds")
    width = min(width, img_w - x)
    height = min(height, img_h - y)
    if width <= 0 or height <= 0:
        raise HTTPException(status_code=400, detail="Tile region outside image bounds")

    key = _build_tile_key(
        shape,
        x=x,
        y=y,
        width=width,
        height=height,
        channel=channel,
        z=z,
        t=t,
    )
    try:
        region = page.asarray(key=key)
    except Exception:
        arr = page.asarray()
        region = np.asarray(arr)[key]  # type: ignore[index]
    return np.asarray(region), width, height


def _thumb_cache_path(asset_id: str) -> Path:
    digest = hashlib.sha256(asset_id.encode("utf-8")).hexdigest()[:16]
    return preview_cache_dir() / f"asset_{digest}.thumb.jpg"


class ImageStreamingService:
    def __init__(self) -> None:
        self.storage = ImageStorageAdapter()
        self.metadata_svc = ImageMetadataService()
        self.jobs = ImageJobQueue()

    def _resolve_or_404(self, asset_id: str) -> dict[str, Any]:
        resolved, reason = self.storage.resolve_asset_detail(asset_id)
        if not resolved:
            if reason.startswith("file_missing:"):
                detail = "Image file not on disk — sync DATABASE_ROOT to this host"
                LOGGER.warning(
                    "image resolve file_missing asset=%s disk_path=%s",
                    asset_id,
                    reason.split(":", 1)[1],
                )
            elif reason.startswith("storage_root_missing:"):
                detail = "Image storage root not configured on this host"
                LOGGER.warning("image resolve %s asset=%s", reason, asset_id)
            else:
                detail = "Image asset not found or unsupported"
                LOGGER.debug("image resolve %s asset=%s", reason, asset_id)
            raise HTTPException(status_code=404, detail=detail)
        return resolved

    def get_metadata(self, asset_id: str) -> dict[str, Any]:
        resolved = self._resolve_or_404(asset_id)
        meta = self.metadata_svc.get_or_stub(
            asset_id=asset_id,
            filename=resolved.get("filename") or "",
            extension=resolved.get("extension") or "",
            size_bytes=int(resolved.get("size_bytes") or 0),
        )
        return {
            "asset_id": asset_id,
            "format": meta.get("format"),
            "streaming_status": meta.get("streaming_status"),
            "image_metadata": meta,
        }

    def build_manifest(self, asset_id: str) -> dict[str, Any]:
        resolved = self._resolve_or_404(asset_id)
        meta = self.metadata_svc.get_or_stub(
            asset_id=asset_id,
            filename=resolved.get("filename") or "",
            extension=resolved.get("extension") or "",
            size_bytes=int(resolved.get("size_bytes") or 0),
        )
        levels = int(meta.get("pyramid_levels") or 1)
        width = meta.get("width")
        height = meta.get("height")
        tile_size = min(MAX_TILE_EDGE, 256)
        dims = meta.get("dimensions") or {}
        axes = dims.get("axes") or ""
        shape = dims.get("shape") or []

        def _axis_count(axis: str) -> int:
            if not axes or axis not in axes or not shape:
                return 1
            return max(1, int(shape[axes.index(axis)]))

        return {
            "asset_id": asset_id,
            "format": meta.get("format"),
            "streaming_status": meta.get("streaming_status"),
            "dimensions": dims,
            "width": width,
            "height": height,
            "channels": meta.get("channels"),
            "z_slices": _axis_count("Z"),
            "timepoints": _axis_count("T"),
            "pyramid_levels": levels,
            "tile_size": tile_size,
            "tile_ready": bool(meta.get("tile_ready")),
            "thumbnail_url": f"/api/assets/{asset_id}/image/thumbnail",
            "metadata_url": f"/api/assets/{asset_id}/image/metadata",
            "stream_url": f"/api/assets/{asset_id}/image/stream",
            "viewer_route": f"#viewer/image/{asset_id}",
            "ome_xml_present": bool(meta.get("ome_xml_present")),
        }

    def inspect_asset(self, asset_id: str) -> dict[str, Any]:
        resolved = self._resolve_or_404(asset_id)
        meta = self.metadata_svc.inspect_file(
            Path(resolved["disk_path"]),
            asset_id=asset_id,
            filename=resolved.get("filename") or "",
            extension=resolved.get("extension") or "",
            size_bytes=int(resolved.get("size_bytes") or 0),
        )
        return {"asset_id": asset_id, "image_metadata": meta}

    def get_thumbnail_bytes(self, asset_id: str) -> tuple[bytes, str]:
        resolved = self._resolve_or_404(asset_id)
        cache_path = _thumb_cache_path(asset_id)
        if cache_path.is_file():
            return cache_path.read_bytes(), "image/jpeg"

        data = self._generate_thumbnail(resolved, cache_path)
        if data:
            return data, "image/jpeg"

        # 1x1 gray JPEG placeholder
        placeholder = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\x27 ,#\x1c\x1c(7),01444\x1f\x27=9=82<.7\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd5\xff\xd9"
        )
        return placeholder, "image/jpeg"

    def _generate_thumbnail(self, resolved: dict[str, Any], dest: Path) -> bytes | None:
        path = Path(resolved["disk_path"])
        asset_id = resolved["asset_id"]
        ext = (resolved.get("extension") or path.suffix or "").lower()
        try:
            from PIL import Image
        except ImportError:
            return None

        # Standard raster images (JPG/PNG/WebP/GIF)
        if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            try:
                with Image.open(path) as im:
                    im = im.convert("RGB") if im.mode not in ("RGB", "L") else im
                    im.thumbnail((DEFAULT_THUMB_EDGE, DEFAULT_THUMB_EDGE))
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    buf = io.BytesIO()
                    im.save(buf, format="JPEG", quality=82, optimize=True)
                    data = buf.getvalue()
                    dest.write_bytes(data)
                    return data
            except Exception as exc:
                LOGGER.debug("raster thumbnail failed %s: %s", asset_id, exc)
                return None

        try:
            import tifffile  # type: ignore
            import numpy as np  # type: ignore
        except ImportError:
            return None

        try:
            with tifffile.TiffFile(str(path)) as tif:
                page = tif.pages[0]
                arr = page.asarray()
                if arr.ndim > 2:
                    arr = arr[0] if arr.shape[0] <= 4 else arr[..., 0]
                arr = np.asarray(arr)
                if arr.dtype != np.uint8:
                    arr = arr.astype(np.float32)
                    arr = (arr - arr.min()) / max(arr.max() - arr.min(), 1e-6) * 255
                    arr = arr.astype(np.uint8)
                im = Image.fromarray(arr)
                im.thumbnail((DEFAULT_THUMB_EDGE, DEFAULT_THUMB_EDGE))
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                dest.parent.mkdir(parents=True, exist_ok=True)
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=82, optimize=True)
                data = buf.getvalue()
                dest.write_bytes(data)
                cached = get_cached_metadata(asset_id) or {}
                cached["thumbnail_ready"] = True
                if cached.get("streaming_status") in (None, "unknown", "metadata_only"):
                    cached["streaming_status"] = "thumbnail_ready"
                set_cached_metadata(asset_id, cached)
                return data
        except Exception as exc:
            LOGGER.debug("thumbnail generation failed %s: %s", asset_id, exc)
            return None

    def get_tile(
        self,
        asset_id: str,
        *,
        level: int = 0,
        x: int = 0,
        y: int = 0,
        width: int = 256,
        height: int = 256,
        channel: int = 0,
        z: int = 0,
        t: int = 0,
        series: int = 0,
        fmt: str = "png",
    ) -> tuple[bytes, str]:
        if width <= 0 or height <= 0:
            raise HTTPException(status_code=400, detail="Invalid tile dimensions")
        if width > MAX_TILE_EDGE or height > MAX_TILE_EDGE:
            raise HTTPException(status_code=400, detail=f"Tile exceeds max edge {MAX_TILE_EDGE}")
        if width * height > MAX_TILE_PIXELS:
            raise HTTPException(status_code=400, detail="Tile region too large")

        resolved = self._resolve_or_404(asset_id)
        try:
            import tifffile  # type: ignore
            import numpy as np  # type: ignore
        except ImportError:
            raise HTTPException(status_code=503, detail="tifffile not available")

        try:
            from PIL import Image
        except ImportError:
            raise HTTPException(status_code=503, detail="Pillow not available")

        path = Path(resolved["disk_path"])
        try:
            with tifffile.TiffFile(str(path)) as tif:
                page = _get_pyramid_page(tif, series=series, level=level)
                region, width, height = _read_tile_region(
                    page,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    channel=channel,
                    z=z,
                    t=t,
                )
        except HTTPException:
            raise
        except Exception as exc:
            LOGGER.warning("tile decode failed for %s: %s", asset_id, exc)
            raise HTTPException(status_code=422, detail="Unable to decode tile region") from exc

        if region.dtype != np.uint8:
            region = region.astype(np.float32)
            region = (region - region.min()) / max(region.max() - region.min(), 1e-6) * 255
            region = region.astype(np.uint8)

        if region.ndim > 2:
            region = np.squeeze(region)
        if region.ndim != 2:
            raise HTTPException(status_code=422, detail="Tile region is not a 2D plane")

        im = Image.fromarray(region)
        buf = io.BytesIO()
        media = "image/png" if fmt.lower() == "png" else "image/jpeg"
        im.save(buf, format="PNG" if media == "image/png" else "JPEG", quality=85)
        return buf.getvalue(), media

    def get_stream_info(self, asset_id: str) -> dict[str, Any]:
        resolved = self._resolve_or_404(asset_id)
        size = self.storage.get_size(resolved)
        return {
            "asset_id": asset_id,
            "size_bytes": size,
            "accepts_ranges": True,
            "content_type": "application/octet-stream",
        }

    def iter_stream(self, asset_id: str, *, start: int | None, end: int | None):
        resolved = self._resolve_or_404(asset_id)
        return self.storage.open_read_stream(resolved, start=start, end=end)

    def readiness_stats(self) -> dict[str, Any]:
        from app_skeleton.api.image_streaming.storage_adapter import is_streamable_image

        rows = []
        from app_skeleton.api import document_library_service as doc_svc

        for row in doc_svc.get_enriched_rows():
            if is_streamable_image(row):
                rows.append(row)

        cache = {}
        from app_skeleton.api.image_streaming.image_metadata_service import _load_cache

        cache = _load_cache()
        status_counts: dict[str, int] = {}
        inspected = 0
        thumb_ready = 0
        tile_ready = 0
        failed = 0
        for row in rows:
            aid = row.get("asset_id") or ""
            meta = (cache.get(aid) or {}).get("image") or {}
            status = meta.get("streaming_status") or "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
            if meta.get("inspected_at"):
                inspected += 1
            if meta.get("thumbnail_ready"):
                thumb_ready += 1
            if meta.get("tile_ready"):
                tile_ready += 1
            if status == "failed":
                failed += 1

        jobs = self.jobs.list_jobs()
        pending_jobs = sum(1 for j in jobs if j.get("status") == "pending")
        failed_jobs = sum(1 for j in jobs if j.get("status") == "failed")

        from app_skeleton.api.imaging_capabilities import probe_imaging_stack

        caps = probe_imaging_stack()
        return {
            "tiff_asset_count": len(rows),
            "inspected_count": inspected,
            "thumbnail_ready_count": thumb_ready,
            "tile_ready_count": tile_ready,
            "failed_count": failed,
            "status_breakdown": status_counts,
            "pending_jobs": pending_jobs,
            "failed_jobs": failed_jobs,
            "streaming_ready": caps.get("streaming_ready"),
            "compression_codecs_ready": caps.get("compression_codecs_ready"),
            "packages": caps.get("packages"),
            "recommendations": caps.get("recommendations"),
        }


def _module_exists(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False
