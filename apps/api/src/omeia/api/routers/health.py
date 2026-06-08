from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from omeia.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

from omeia.security.auth import require_platform_user, require_admin_user

router = APIRouter()

@router.get("/metrics")
def metrics() -> dict:
    """Basic in-memory request metrics (enable with ENABLE_REQUEST_METRICS=true)."""
    from omeia.api.middleware.metrics import metrics_enabled, snapshot_metrics
    from omeia.api.observability import timing_snapshot
    from omeia.api.db_pool import pool_available

    data = snapshot_metrics()
    if not metrics_enabled():
        return {"enabled": False, "message": "Set ENABLE_REQUEST_METRICS=true to collect request metrics."}
    data["timings"] = timing_snapshot()
    data["postgres_pool"] = pool_available()
    return data


@router.get("/live")
def live() -> dict:
    """Process-level liveness — cheap, always 200 when the API process is up."""
    return {"status": "alive"}


@router.get("/ready")
def ready(response: Response) -> dict:
    """Readiness — 503 when required dependencies (Postgres, optional Qdrant/LLM) are unavailable."""
    from omeia.api.readiness import check_readiness

    report = check_readiness(db_conn=DB_CONN, qdrant_client=qdrant_client, llm_client=llm_client)
    if not report["ready"]:
        response.status_code = 503
    return report


@router.get("/health")
def health() -> dict:
    from omeia.api.connector_status import production_connectors_summary
    from omeia.api.docker_service_client import docker_services
    from omeia.api.readiness import check_readiness

    readiness = check_readiness(db_conn=DB_CONN, qdrant_client=qdrant_client, llm_client=llm_client)
    checks = readiness.get("checks") or {}

    return {
        "status": readiness.get("status") or "ok",
        "ready": readiness.get("ready", True),
        "database_connected": checks.get("database_connected", False),
        "llm_client_provider": llm_client.provider,
        "llm_client_healthy": checks.get("llm_healthy", llm_client.healthCheck()),
        "docker_services": docker_services.public_status(),
        "connectors": production_connectors_summary(),
        "blockers": readiness.get("blockers") or [],
    }

@router.get("/api/processor/status")
def processor_status() -> dict:
    """Public health-style status for the OS-level autonomous processor daemon."""
    from omeia.api.processor_status import read_processor_status

    return read_processor_status()

@router.get("/api/platform/scheduled-scanner/status")
def scheduled_scanner_status() -> dict:
    """Last run, config, and thread state for the scheduled directory scanner."""
    from omeia.api.scheduled_directory_scanner import scheduled_directory_scanner

    return scheduled_directory_scanner.status()

@router.get("/stats")
def stats(project_code: Optional[List[str]] = Query(None)) -> dict:
    return query_postgres_metadata(project_code)

@router.get("/api/platform/connectors")
def platform_connectors_status() -> dict:
    """Firebase / Supabase / storage connector readiness — no secrets."""
    from omeia.api.connector_status import production_connectors_summary

    return production_connectors_summary()

class RegisterRequestBody(BaseModel):
    email: str = Field(..., min_length=3)
    display_name: str = Field(..., min_length=1, max_length=120)
    organization: str = Field(..., min_length=1, max_length=200)


@router.post("/api/auth/register-request")
def auth_register_request(body: RegisterRequestBody) -> dict:
    """Public registration hook after Firebase account creation (no password stored server-side)."""
    try:
        result = platform_admin.create_registration_request(
            body.email,
            display_name=body.display_name,
            organization=body.organization,
        )
        return {"ok": True, **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/auth/config")
def auth_config_public() -> dict:
    """Firebase web client config + Email/Password-only policy (no Google Sign-In)."""
    from omeia.security.auth import AUTH_ALLOW_SKIP, AUTH_DISABLED
    from omeia.api.firebase_config import firebase_client_config_public

    return {
        "auth_disabled": AUTH_DISABLED,
        "auth_allow_skip": AUTH_ALLOW_SKIP and not AUTH_DISABLED,
        "firebase": firebase_client_config_public(),
    }

@router.post("/api/projects/{project_code}/knowledge/ingest", dependencies=[Depends(require_platform_user)])
def project_knowledge_ingest(project_code: str) -> dict:
    try:
        return extract_and_ingest_project(project_code)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/page-domains", dependencies=[Depends(require_platform_user)])
def page_domains_list() -> dict:
    return {"domains": list_domains(), "sections": list_page_sections()}

@router.get("/api/admin/allowed-emails", dependencies=[Depends(require_admin_user)])
def admin_allowed_emails() -> dict:
    return {"emails": platform_admin.list_allowed_emails()}

@router.post("/api/admin/allowed-emails", dependencies=[Depends(require_admin_user)])
def admin_add_allowed_email(email: str = Query(...), status: str = Query("approved")) -> dict:
    return platform_admin.upsert_allowed_email(email, status=status)

@router.get("/api/admin/registration-requests", dependencies=[Depends(require_admin_user)])
def admin_registration_requests(status: Optional[str] = Query("pending")) -> dict:
    return {"requests": platform_admin.list_registration_requests(status=status)}

@router.get("/api/admin/ingestion-jobs", dependencies=[Depends(require_admin_user)])
def admin_ingestion_jobs(limit: int = Query(20, ge=1, le=100)) -> dict:
    return {"jobs": platform_admin.list_ingestion_jobs(limit=limit)}

@router.get("/api/admin/review-tasks", dependencies=[Depends(require_admin_user)])
def admin_review_tasks(limit: int = Query(50, ge=1, le=200)) -> dict:
    return {"tasks": platform_admin.list_review_tasks(limit=limit)}