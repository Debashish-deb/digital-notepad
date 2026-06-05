from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from app_skeleton.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

@router.get("/health")
def health() -> dict:
    db_ok = True
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            pass
    except Exception:
        db_ok = False
        
    from app_skeleton.api.connector_status import production_connectors_summary

    return {
        "status": "ok",
        "database_connected": db_ok,
        "llm_client_provider": llm_client.provider,
        "llm_client_healthy": llm_client.healthCheck(),
        "connectors": production_connectors_summary(),
    }

@router.get("/api/processor/status")
def processor_status() -> dict:
    """Public health-style status for the OS-level autonomous processor daemon."""
    from app_skeleton.api.processor_status import read_processor_status

    return read_processor_status()

@router.get("/stats")
def stats(project_code: Optional[List[str]] = Query(None)) -> dict:
    return query_postgres_metadata(project_code)

@router.get("/api/platform/connectors")
def platform_connectors_status() -> dict:
    """Firebase / Supabase / storage connector readiness — no secrets."""
    from app_skeleton.api.connector_status import production_connectors_summary

    return production_connectors_summary()

@router.get("/api/auth/config")
def auth_config_public() -> dict:
    """Firebase web client config + Email/Password-only policy (no Google Sign-In)."""
    from app_skeleton.api.auth_firebase import AUTH_DISABLED
    from app_skeleton.api.firebase_config import firebase_client_config_public

    return {
        "auth_disabled": AUTH_DISABLED,
        "firebase": firebase_client_config_public(),
    }

@router.post("/api/projects/{project_code}/knowledge/ingest")
def project_knowledge_ingest(project_code: str) -> dict:
    try:
        return extract_and_ingest_project(project_code)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/page-domains")
def page_domains_list() -> dict:
    return {"domains": list_domains(), "sections": list_page_sections()}

@router.get("/api/admin/allowed-emails")
def admin_allowed_emails() -> dict:
    return {"emails": platform_admin.list_allowed_emails()}

@router.post("/api/admin/allowed-emails")
def admin_add_allowed_email(email: str = Query(...), status: str = Query("approved")) -> dict:
    return platform_admin.upsert_allowed_email(email, status=status)

@router.get("/api/admin/registration-requests")
def admin_registration_requests(status: Optional[str] = Query("pending")) -> dict:
    return {"requests": platform_admin.list_registration_requests(status=status)}

@router.get("/api/admin/ingestion-jobs")
def admin_ingestion_jobs(limit: int = Query(20, ge=1, le=100)) -> dict:
    return {"jobs": platform_admin.list_ingestion_jobs(limit=limit)}

@router.get("/api/admin/review-tasks")
def admin_review_tasks(limit: int = Query(50, ge=1, le=200)) -> dict:
    return {"tasks": platform_admin.list_review_tasks(limit=limit)}