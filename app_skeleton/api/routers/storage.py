from app_skeleton.security.permissions import require_role
from app_skeleton.security.auth import require_platform_user
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from app_skeleton.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

@router.get("/api/storage/roots", dependencies=_FIREBASE_PROTECTED)
def storage_roots_list() -> dict:
    """Phase 1: logical storage providers (configured flags only, no paths)."""
    from app_skeleton.api.paths import storage_roots_public_summary
    from app_skeleton.api.connector_status import production_connectors_summary

    return {
        "providers": storage_roots_public_summary(),
        "production_connectors": production_connectors_summary(),
    }

@router.get("/api/storage/connectors/status", dependencies=_FIREBASE_PROTECTED)
def storage_connectors_status() -> dict:
    return {
        "connectors": [
            datacloud_webdav.public_status(),
            pdrive_smb.public_status(),
            {
                "provider_id": "supabase_storage",
                "configured": bool(
                    os.getenv("SUPABASE_URL", "").strip()
                    and (
                        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
                        or os.getenv("SERVICE_ROLE_KEY", "").strip()
                    )
                ),
                "role": "small_files_previews",
            },
        ]
    }

@router.get("/api/storage/datacloud/list", dependencies=_FIREBASE_PROTECTED)
def storage_datacloud_list(relative_path: str = Query(""), depth: int = Query(1, ge=1, le=3)) -> dict:
    return {"entries": datacloud_webdav.list_logical_directory(relative_path, depth=depth)}

@router.get("/api/storage/datacloud/scan", dependencies=_FIREBASE_PROTECTED)
def storage_datacloud_scan(
    relative_path: str = Query(""),
    max_entries: int = Query(200, ge=1, le=2000),
) -> dict:
    return datacloud_webdav.scan_tree(relative_path, max_entries=max_entries)

@router.get("/api/storage/datacloud/manifest", dependencies=_FIREBASE_PROTECTED)
def storage_datacloud_manifest(
    relative_path: str = Query(""),
    max_entries: int = Query(500, ge=1, le=5000),
) -> dict:
    return datacloud_webdav.build_manifest(relative_path, max_entries=max_entries)

@router.get("/api/storage/pdrive/list", dependencies=_FIREBASE_PROTECTED)
def storage_pdrive_list(relative_path: str = Query("")) -> dict:
    return {"entries": pdrive_smb.list_logical_directory(relative_path)}

@router.get("/api/storage/pdrive/scan", dependencies=_FIREBASE_PROTECTED)
def storage_pdrive_scan(
    relative_path: str = Query(""),
    max_entries: int = Query(200, ge=1, le=2000),
) -> dict:
    return pdrive_smb.scan_tree(relative_path, max_entries=max_entries)

@router.get("/api/storage/pdrive/manifest", dependencies=_FIREBASE_PROTECTED)
def storage_pdrive_manifest(
    relative_path: str = Query(""),
    max_entries: int = Query(500, ge=1, le=5000),
) -> dict:
    return pdrive_smb.build_manifest(relative_path, max_entries=max_entries)

@router.get("/api/storage/datacloud/download", dependencies=_FIREBASE_PROTECTED)
def storage_datacloud_download(relative_path: str = Query(..., min_length=1)) -> StreamingResponse:
    """Backend-only stream; never expose WebDAV URL to clients."""
    if not datacloud_webdav.is_configured():
        raise HTTPException(status_code=503, detail="DataCloud not configured")
    return StreamingResponse(
        datacloud_webdav.download_stream(relative_path),
        media_type="application/octet-stream",
    )

@router.get("/api/storage/pdrive/download", dependencies=_FIREBASE_PROTECTED)
def storage_pdrive_download(relative_path: str = Query(..., min_length=1)) -> StreamingResponse:
    if not pdrive_smb.is_configured():
        raise HTTPException(status_code=503, detail="P-drive not configured")
    return StreamingResponse(
        pdrive_smb.download_stream(relative_path),
        media_type="application/octet-stream",
    )

@router.post("/api/storage/ingest/{provider_id}", dependencies=_FIREBASE_PROTECTED)
def storage_ingest_provider(
    provider_id: str,
    relative_path: str = Query(""),
    max_entries: int = Query(500, ge=1, le=5000),
) -> dict:
    """Scan → manifest → platform.storage_objects (metadata only)."""
    if provider_id not in ("datacloud_webdav", "pdrive_smb"):
        raise HTTPException(status_code=400, detail="Unsupported storage provider")
    job = platform_admin.create_ingestion_job(f"storage_scan_{provider_id}")
    try:
        result = storage_ingestion.ingest_provider_scan(
            provider_id, relative_path, max_entries=max_entries
        )
        items = (result.get("persist") or {}).get("upserted", 0)
        platform_admin.finish_ingestion_job(job["job_id"], items_processed=items)
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc