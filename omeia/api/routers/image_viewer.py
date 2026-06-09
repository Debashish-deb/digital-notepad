"""Authenticated image viewer extensions — ROIs, overlays, presets, histogram, cell inspect."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from omeia.api.image_streaming.image_streaming_service import ImageStreamingService
from omeia.api.image_streaming.image_viewer_store import (
    create_overlay,
    create_roi,
    delete_channel_preset,
    delete_overlay,
    delete_roi,
    inspect_cell,
    list_channel_presets,
    list_overlays,
    list_rois,
    save_channel_preset,
)
from omeia.api.image_streaming.permissions import can_access_image_asset
from omeia.api.image_streaming.storage_adapter import lookup_asset_row
from omeia.api.platform_flags import image_enable_roi_annotations
from omeia.security.auth import require_platform_user
from omeia.security.audit_log import log_image_access

router = APIRouter(tags=["image-viewer"])

_streaming = ImageStreamingService()


def _check_access(user: dict[str, Any], asset_id: str) -> dict[str, Any]:
    row = lookup_asset_row(asset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not can_access_image_asset(user, row):
        raise HTTPException(status_code=403, detail="Not authorized for this image asset")
    return row


class RoiCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    geometry: dict[str, Any]
    roi_type: str = Field(default="rectangle", pattern="^(rectangle|polygon|freehand|point)$")
    project: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class OverlayCreateBody(BaseModel):
    overlay_asset_id: str = Field(..., min_length=1)
    overlay_type: str = Field(
        default="cell",
        pattern="^(mesmer|stardist|cell|nucleus|heatmap|custom)$",
    )
    label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChannelPresetBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    channels: list[dict[str, Any]] = Field(default_factory=list)
    preset_id: str | None = None


@router.get("/api/assets/{asset_id}/image/rois")
def get_rois(
    asset_id: str,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    log_image_access(user.get("email", "unknown"), asset_id, "rois/list")
    email = user.get("email") or "unknown"
    return {"asset_id": asset_id, "rois": list_rois(asset_id=asset_id, user_email=email)}


@router.post("/api/assets/{asset_id}/image/rois")
def post_roi(
    asset_id: str,
    body: RoiCreateBody,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    if not image_enable_roi_annotations():
        raise HTTPException(status_code=403, detail="ROI annotations disabled")
    log_image_access(user.get("email", "unknown"), asset_id, "rois/create")
    email = user.get("email") or "unknown"
    roi = create_roi(
        asset_id=asset_id,
        user_email=email,
        name=body.name,
        geometry=body.geometry,
        roi_type=body.roi_type,
        project=body.project,
        description=body.description,
        tags=body.tags,
    )
    return {"roi": roi}


@router.delete("/api/assets/{asset_id}/image/rois/{roi_id}")
def remove_roi(
    asset_id: str,
    roi_id: str,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    if not image_enable_roi_annotations():
        raise HTTPException(status_code=403, detail="ROI annotations disabled")
    email = user.get("email") or "unknown"
    ok = delete_roi(roi_id=roi_id, asset_id=asset_id, user_email=email)
    if not ok:
        raise HTTPException(status_code=404, detail="ROI not found")
    return {"deleted": True, "roi_id": roi_id}


@router.get("/api/assets/{asset_id}/image/overlays")
def get_overlays(
    asset_id: str,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    log_image_access(user.get("email", "unknown"), asset_id, "overlays/list")
    return {"asset_id": asset_id, "overlays": list_overlays(asset_id=asset_id)}


@router.post("/api/assets/{asset_id}/image/overlays")
def post_overlay(
    asset_id: str,
    body: OverlayCreateBody,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    log_image_access(user.get("email", "unknown"), asset_id, "overlays/create")
    overlay = create_overlay(
        asset_id=asset_id,
        overlay_asset_id=body.overlay_asset_id,
        overlay_type=body.overlay_type,
        label=body.label,
        metadata=body.metadata,
    )
    return {"overlay": overlay}


@router.delete("/api/assets/{asset_id}/image/overlays/{overlay_id}")
def remove_overlay(
    asset_id: str,
    overlay_id: str,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    ok = delete_overlay(overlay_id=overlay_id, asset_id=asset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Overlay not found")
    return {"deleted": True, "overlay_id": overlay_id}


@router.get("/api/users/me/image/channel-presets")
def get_my_channel_presets(
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    email = user.get("email") or "unknown"
    return {"presets": list_channel_presets(user_email=email)}


@router.post("/api/users/me/image/channel-presets")
def post_channel_preset(
    body: ChannelPresetBody,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    email = user.get("email") or "unknown"
    preset = save_channel_preset(
        user_email=email,
        name=body.name,
        channels=body.channels,
        preset_id=body.preset_id,
    )
    return {"preset": preset}


@router.delete("/api/users/me/image/channel-presets/{preset_id}")
def remove_channel_preset(
    preset_id: str,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    email = user.get("email") or "unknown"
    ok = delete_channel_preset(preset_id=preset_id, user_email=email)
    if not ok:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"deleted": True, "preset_id": preset_id}


@router.get("/api/assets/{asset_id}/image/cells/{cell_id}")
def get_cell_inspection(
    asset_id: str,
    cell_id: str,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    log_image_access(user.get("email", "unknown"), asset_id, f"cell/{cell_id}")
    overlays = list_overlays(asset_id=asset_id)
    overlay_md = {}
    for ov in overlays:
        if ov.get("overlay_type") in ("cell", "nucleus", "mesmer", "stardist"):
            overlay_md = ov.get("metadata") or {}
            break
    return inspect_cell(asset_id=asset_id, cell_id=cell_id, overlay_metadata=overlay_md)


@router.get("/api/assets/{asset_id}/image/pixel")
def get_pixel_probe(
    asset_id: str,
    x: int = Query(..., ge=0),
    y: int = Query(..., ge=0),
    z: int = Query(0, ge=0),
    t: int = Query(0, ge=0),
    level: int = Query(0, ge=0, le=32),
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    log_image_access(user.get("email", "unknown"), asset_id, f"pixel/{x}/{y}")
    return _streaming.sample_pixel_probe(asset_id, x=x, y=y, z=z, t=t, level=level)


@router.get("/api/assets/{asset_id}/image/histogram")
def get_histogram(
    asset_id: str,
    channel: int = Query(0, ge=0),
    z: int = Query(0, ge=0),
    t: int = Query(0, ge=0),
    x: int = Query(0, ge=0),
    y: int = Query(0, ge=0),
    width: int = Query(256, ge=1, le=512),
    height: int = Query(256, ge=1, le=512),
    bins: int = Query(256, ge=16, le=512),
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    log_image_access(user.get("email", "unknown"), asset_id, f"histogram/ch{channel}")
    return _streaming.sample_histogram(
        asset_id,
        channel=channel,
        z=z,
        t=t,
        x=x,
        y=y,
        width=width,
        height=height,
        bins=bins,
    )
