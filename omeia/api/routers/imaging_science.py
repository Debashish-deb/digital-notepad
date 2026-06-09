"""Scientific imaging extensions — knowledge graph, council, spatial stubs."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from omeia.api.imaging_council_service import run_imaging_council
from omeia.api.imaging_knowledge_bridge import build_marker_graph
from omeia.api.image_streaming.image_streaming_service import ImageStreamingService
from omeia.api.image_streaming.permissions import can_access_image_asset
from omeia.api.image_streaming.storage_adapter import lookup_asset_row
from omeia.api.image_streaming.spatial_analysis import compute_spatial_metrics
from omeia.security.auth import require_platform_user
from omeia.security.audit_log import log_image_access

router = APIRouter(tags=["imaging-science"])

_streaming = ImageStreamingService()


def _check_access(user: dict[str, Any], asset_id: str) -> dict[str, Any]:
    row = lookup_asset_row(asset_id)
    if not row:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Asset not found")
    if not can_access_image_asset(user, row):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Not authorized for this image asset")
    return row


class CouncilAnalyzeBody(BaseModel):
    asset_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=4000)
    markers: list[str] = Field(default_factory=list)
    project: str | None = None


class SpatialAnalyzeBody(BaseModel):
    radius_um: float = Field(default=50.0, gt=0, le=500)
    phenotype_filter: str | None = None


@router.get("/api/imaging/markers/graph")
def get_marker_graph(
    channel_names: list[str] = Query(default=[]),
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    return build_marker_graph(channel_names or None)


@router.post("/api/imaging/council/analyze")
def post_council_analyze(
    body: CouncilAnalyzeBody,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    asset_id = body.asset_id
    _check_access(user, asset_id)
    log_image_access(user.get("email", "unknown"), asset_id, "council/analyze")
    manifest = _streaming.build_manifest(asset_id)
    imaging_context = {
        "dtype": manifest.get("dtype"),
        "pixel_size_um": manifest.get("physical_pixel_size_um"),
        "channels": manifest.get("channel_names"),
        "project": body.project,
    }
    llm = None
    try:
        from omeia.api.llm_factory import get_llm

        llm = get_llm()
    except Exception:
        pass
    return run_imaging_council(
        asset_id=asset_id,
        question=body.question,
        markers=body.markers or manifest.get("channel_names") or [],
        imaging_context=imaging_context,
        llm=llm,
    )


@router.post("/api/assets/{asset_id}/image/spatial/analyze")
def post_spatial_analyze(
    asset_id: str,
    body: SpatialAnalyzeBody,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    _check_access(user, asset_id)
    log_image_access(user.get("email", "unknown"), asset_id, "spatial/analyze")
    manifest = _streaming.build_manifest(asset_id)
    from omeia.api.image_streaming.image_viewer_store import list_overlays

    overlay_md: dict[str, Any] = {}
    for ov in list_overlays(asset_id=asset_id):
        if ov.get("overlay_type") in ("cell", "nucleus", "mesmer", "stardist"):
            overlay_md = ov.get("metadata") or {}
            break
    um_per_px = manifest.get("physical_pixel_size_um") or manifest.get("pixel_size_um")
    return compute_spatial_metrics(
        overlay_metadata=overlay_md,
        radius_um=body.radius_um,
        um_per_pixel=um_per_px,
        phenotype_filter=body.phenotype_filter,
    )
