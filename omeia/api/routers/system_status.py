"""System / compute status for admin dashboards (Phase 14)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from omeia.api.compute_profile_service import build_compute_status
from omeia.api.model_runtime_selector import select_runtime
from omeia.security.auth import require_admin_user, require_platform_user

router = APIRouter(tags=["system-status"])


@router.get("/api/system/compute-status")
def compute_status(user: dict = Depends(require_platform_user)) -> dict[str, Any]:
    return build_compute_status()


@router.get("/api/system/compute-status/admin")
def compute_status_admin(user: dict = Depends(require_admin_user)) -> dict[str, Any]:
    status = build_compute_status()
    status["runtime_samples"] = {
        "greeting": select_runtime("greeting"),
        "ocr": select_runtime("ocr"),
        "image_tile": select_runtime("image_tile"),
        "image_segment": select_runtime("image_segment", sensitive=True),
        "strategy_report": select_runtime("strategy_report", sensitive=True),
    }
    return status


@router.get("/api/system/status-dashboard")
def status_dashboard(user: dict = Depends(require_admin_user)) -> dict[str, Any]:
    """Lightweight ops dashboard payload (extend with job queues in follow-up)."""
    from omeia.api.readiness import check_readiness
    from omeia.api.common import DB_CONN, qdrant_client, llm_client

    compute = build_compute_status()
    readiness = check_readiness(db_conn=DB_CONN, qdrant_client=qdrant_client, llm_client=llm_client)
    return {
        "compute": compute,
        "readiness": readiness,
        "dashboard_sections": [
            "sync_health",
            "compute_profile",
            "job_queues",
            "model_capability",
            "evidence_coverage",
            "image_viewer_mode",
        ],
        "note": "Job queue and evidence coverage counts wired in follow-up PRs.",
    }
