"""Authenticated image asset streaming API."""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from omeia.api.image_streaming.image_streaming_service import ImageStreamingService
from omeia.api.image_streaming.permissions import can_access_image_asset, require_admin
from omeia.api.image_streaming.storage_adapter import lookup_asset_row
from omeia.security.auth import require_admin_user, require_platform_user
from omeia.security.audit_log import log_admin_operation, log_image_access

router = APIRouter(tags=["image-assets"])

_svc = ImageStreamingService()

_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")


class InspectRequest(BaseModel):
    asset_ids: list[str] = Field(default_factory=list, max_length=100)


def _check_access(user: dict[str, Any], asset_id: str) -> dict[str, Any]:
    row = lookup_asset_row(asset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not can_access_image_asset(user, row):
        raise HTTPException(status_code=403, detail="Not authorized for this image asset")
    return row


def _log_image_access(user: dict[str, Any], asset_id: str, action: str) -> None:
    log_image_access(user.get("email", "unknown"), asset_id, action)


@router.get("/api/assets/{asset_id}/image/metadata")
def image_metadata(
    asset_id: str,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    _log_image_access(user, asset_id, "metadata")
    result = _svc.get_metadata(asset_id)
    return _public_response(result)


@router.get("/api/assets/{asset_id}/image/manifest")
def image_manifest(
    asset_id: str,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    _log_image_access(user, asset_id, "manifest")
    return _public_response(_svc.build_manifest(asset_id))


@router.get("/api/assets/{asset_id}/image/thumbnail")
def image_thumbnail(
    asset_id: str,
    user: dict[str, Any] = Depends(require_platform_user),
) -> Response:
    _check_access(user, asset_id)
    _log_image_access(user, asset_id, "thumbnail")
    data, media_type = _svc.get_thumbnail_bytes(asset_id)
    return Response(content=data, media_type=media_type, headers={"Cache-Control": "private, max-age=3600"})


@router.get("/api/assets/{asset_id}/image/tile")
def image_tile(
    asset_id: str,
    level: int = Query(0, ge=0, le=32),
    x: int = Query(0, ge=0),
    y: int = Query(0, ge=0),
    width: int = Query(256, ge=1, le=512),
    height: int = Query(256, ge=1, le=512),
    channel: int = Query(0, ge=0),
    z: int = Query(0, ge=0),
    t: int = Query(0, ge=0),
    series: int = Query(0, ge=0),
    format: str = Query("png", pattern="^(png|jpeg|jpg)$"),
    window_min: float | None = Query(None),
    window_max: float | None = Query(None),
    user: dict[str, Any] = Depends(require_platform_user),
) -> Response:
    _check_access(user, asset_id)
    _log_image_access(user, asset_id, f"tile/{level}/{x}/{y}")
    fmt = "jpeg" if format == "jpg" else format
    data, media_type = _svc.get_tile(
        asset_id,
        level=level,
        x=x,
        y=y,
        width=width,
        height=height,
        channel=channel,
        z=z,
        t=t,
        series=series,
        fmt=fmt,
        window_min=window_min,
        window_max=window_max,
    )
    return Response(content=data, media_type=media_type, headers={"Cache-Control": "private, max-age=300"})


@router.get("/api/assets/{asset_id}/image/stream")
def image_stream(
    asset_id: str,
    request: Request,
    user: dict[str, Any] = Depends(require_platform_user),
) -> Response:
    _check_access(user, asset_id)
    _log_image_access(user, asset_id, "stream")
    info = _svc.get_stream_info(asset_id)
    size = int(info["size_bytes"])
    range_header = request.headers.get("range") or request.headers.get("Range")
    start = 0
    end = size - 1

    if range_header:
        match = _RANGE_RE.match(range_header.strip())
        if not match:
            raise HTTPException(status_code=416, detail="Invalid Range header")
        start = int(match.group(1))
        if match.group(2):
            end = int(match.group(2))
        end = min(end, size - 1)
        if start > end or start >= size:
            raise HTTPException(status_code=416, detail="Range not satisfiable")
        content_length = end - start + 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": info["content_type"],
        }
        return StreamingResponse(
            _svc.iter_stream(asset_id, start=start, end=end),
            status_code=206,
            headers=headers,
            media_type=info["content_type"],
        )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(size),
        "Content-Type": info["content_type"],
    }
    return StreamingResponse(
        _svc.iter_stream(asset_id, start=0, end=size - 1),
        headers=headers,
        media_type=info["content_type"],
    )


@router.get("/api/admin/image-streaming/readiness")
def admin_readiness(
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    log_admin_operation(user.get("email", "unknown"), "readiness_check", "image_streaming")
    return _svc.readiness_stats()


@router.get("/api/admin/image-streaming/capabilities")
def admin_capabilities(
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    """Report installed imaging libraries on this API host (no external API substitutes for TIFF I/O)."""
    from omeia.api.imaging_capabilities import probe_imaging_stack

    log_admin_operation(user.get("email", "unknown"), "capabilities_check", "image_streaming")
    return probe_imaging_stack()


@router.post("/api/admin/image-streaming/inspect")
def admin_inspect(
    body: InspectRequest,
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    if not body.asset_ids:
        raise HTTPException(status_code=400, detail="asset_ids required")
    log_admin_operation(user.get("email", "unknown"), "inspect", f"{len(body.asset_ids)} assets")
    jobs = _svc.jobs.enqueue_many("inspect_image_metadata", body.asset_ids)
    results = []
    for job in jobs:
        try:
            out = _svc.inspect_asset(job["asset_id"])
            _svc.jobs.mark_done(job["job_id"])
            results.append({"asset_id": job["asset_id"], "status": "done", "metadata": out.get("image_metadata")})
        except HTTPException as exc:
            _svc.jobs.mark_failed(job["job_id"], str(exc.detail))
            results.append({"asset_id": job["asset_id"], "status": "failed", "error": exc.detail})
        except Exception as exc:
            _svc.jobs.mark_failed(job["job_id"], str(exc))
            results.append({"asset_id": job["asset_id"], "status": "failed", "error": str(exc)})
    return {"queued": len(jobs), "results": results}


@router.post("/api/admin/image-streaming/retry-failed")
def admin_retry_failed(
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    log_admin_operation(user.get("email", "unknown"), "retry_failed", "image_streaming_jobs")
    count = _svc.jobs.retry_failed()
    return {"retried": count}


def _public_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip any accidental path fields from API responses."""
    blocked = {"disk_path", "logical_path", "original_path", "provider", "source", "preview_path"}
    if isinstance(payload, dict):
        return {k: v for k, v in payload.items() if k not in blocked}
    return payload
