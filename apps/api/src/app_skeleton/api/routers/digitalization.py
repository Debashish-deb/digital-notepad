"""FastAPI routes for the data digitalization pipeline."""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import psycopg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app_skeleton.security.auth import require_admin_user, require_platform_user
from app_skeleton.security.permissions import require_role
from app_skeleton.api.ocr.adapter import ocr_enabled
from pydantic import BaseModel, Field

LOGGER = logging.getLogger(__name__)
router = APIRouter()


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn
    return postgres_conn()


def _safe_path(logical_path: str) -> str:
    """Strip absolute path components — never expose server paths to frontend."""
    if not logical_path:
        return ""
    # Remove leading absolute path segments
    parts = logical_path.replace("\\", "/").split("/")
    # Keep only relative parts (after common roots)
    return "/".join(parts)


# ── Status ────────────────────────────────────────────────────

@router.get("/api/digitalization/status")
def digitalization_status() -> dict:
    """Counts by pipeline status."""
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT status, COUNT(*) FROM platform.source_file_manifest GROUP BY status;
                """)
                manifest_counts = {r[0]: r[1] for r in cur.fetchall()}

                cur.execute("SELECT COUNT(*) FROM platform.extracted_document;")
                extracted_total = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.canonical_document;")
                canonical_total = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.canonical_document WHERE needs_review = true;")
                needs_review = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.document_chunk;")
                chunks_total = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.canonical_document WHERE should_index = true AND validation_status = 'validated';")
                ready_for_rag = cur.fetchone()[0]

                ocr_counts: dict[str, int] = {}
                try:
                    cur.execute("SELECT status, COUNT(*) FROM platform.ocr_job GROUP BY status;")
                    ocr_counts = {r[0]: r[1] for r in cur.fetchall()}
                except Exception:
                    ocr_counts = {}

        return {
            "manifest_by_status": manifest_counts,
            "discovered": sum(manifest_counts.values()),
            "extracted": extracted_total,
            "canonicalized": canonical_total,
            "needs_review": needs_review,
            "chunks_total": chunks_total,
            "ready_for_rag": ready_for_rag,
            "failed": manifest_counts.get("extraction_failed", 0) + manifest_counts.get("validation_failed", 0),
            "needs_ocr": manifest_counts.get("needs_ocr", 0),
            "ocr_enabled": ocr_enabled(),
            "ocr_jobs_by_status": ocr_counts,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Scan ──────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    provider: str = "local"
    root_path: str = ""
    dry_run: bool = True
    max_files: int = 100


@router.post("/api/digitalization/scan")
def digitalization_scan(req: ScanRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Trigger manifest scan (discovery only)."""
    from app_skeleton.digitalization.ingestion_job import run_digitalization
    result = run_digitalization(
        provider=req.provider,
        root_path=req.root_path,
        dry_run=True,
        max_files=req.max_files,
    )
    return result


# ── Run ───────────────────────────────────────────────────────

class RunRequest(BaseModel):
    provider: str = "local"
    root_path: str = ""
    dry_run: bool = False
    max_files: int = 100


@router.post("/api/digitalization/run")
def digitalization_run(req: RunRequest, background_tasks: BackgroundTasks, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Run full digitalization pipeline."""
    from app_skeleton.digitalization.ingestion_job import run_digitalization

    if req.dry_run:
        return run_digitalization(
            provider=req.provider,
            root_path=req.root_path,
            dry_run=True,
            max_files=req.max_files,
        )

    # Run in background for large jobs
    if req.max_files > 50:
        background_tasks.add_task(
            run_digitalization,
            provider=req.provider,
            root_path=req.root_path,
            dry_run=False,
            max_files=req.max_files,
        )
        return {"status": "started_background", "max_files": req.max_files}

    return run_digitalization(
        provider=req.provider,
        root_path=req.root_path,
        dry_run=False,
        max_files=req.max_files,
    )


# ── Documents ─────────────────────────────────────────────────

@router.get("/api/digitalization/documents")
def digitalization_documents(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    domain: Optional[str] = None,
    document_type: Optional[str] = None,
    needs_review: Optional[bool] = None,
) -> dict:
    """List canonical documents."""
    try:
        clauses = ["1=1"]
        params: list[Any] = []
        if domain:
            clauses.append("cd.domain = %s")
            params.append(domain)
        if document_type:
            clauses.append("cd.document_type = %s")
            params.append(document_type)
        if needs_review is not None:
            clauses.append("cd.needs_review = %s")
            params.append(needs_review)

        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT COUNT(*) FROM platform.canonical_document cd WHERE {' AND '.join(clauses)};
                """, params)
                total = cur.fetchone()[0]

                cur.execute(f"""
                    SELECT
                        cd.document_id, cd.title, cd.document_type, cd.domain,
                        cd.validation_status, cd.needs_review, cd.should_index,
                        cd.short_summary, cd.warnings,
                        sfm.logical_path, sfm.provider, sfm.file_ext, sfm.status AS manifest_status,
                        (SELECT COUNT(*) FROM platform.document_chunk dc WHERE dc.canonical_document_id = cd.id) AS chunk_count,
                        cd.created_at
                    FROM platform.canonical_document cd
                    JOIN platform.source_file_manifest sfm ON sfm.id = cd.manifest_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY cd.created_at DESC
                    OFFSET %s LIMIT %s;
                """, params + [offset, limit])
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]

        # Sanitize paths
        for row in rows:
            row["logical_path"] = _safe_path(row.get("logical_path", ""))
            if row.get("warnings") and isinstance(row["warnings"], str):
                row["warnings"] = json.loads(row["warnings"])

        return {"total": total, "offset": offset, "limit": limit, "documents": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Document detail ───────────────────────────────────────────

@router.get("/api/digitalization/documents/{document_id}")
def digitalization_document_detail(document_id: str) -> dict:
    """Return canonical JSON and text preview — never secrets."""
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        cd.document_id, cd.title, cd.document_type, cd.domain,
                        cd.canonical_json, cd.canonical_text, cd.short_summary,
                        cd.validation_status, cd.needs_review, cd.should_index, cd.warnings,
                        sfm.logical_path, sfm.provider, sfm.file_ext, sfm.status AS manifest_status,
                        ed.extraction_status, ed.extraction_confidence, ed.extractor_name,
                        ed.raw_tables
                    FROM platform.canonical_document cd
                    JOIN platform.source_file_manifest sfm ON sfm.id = cd.manifest_id
                    LEFT JOIN platform.extracted_document ed ON ed.id = cd.extracted_document_id
                    WHERE cd.document_id = %s;
                """, (document_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Document not found")
                cols = [d[0] for d in cur.description]
                doc = dict(zip(cols, row))

        # Sanitize
        doc["logical_path"] = _safe_path(doc.get("logical_path", ""))
        # Strip credentials_or_secrets from canonical_json
        cj = doc.get("canonical_json")
        if isinstance(cj, str):
            cj = json.loads(cj)
        if isinstance(cj, dict):
            sd = cj.get("structured_data", {})
            if "credentials_or_secrets" in sd:
                sd["credentials_or_secrets"] = [
                    {"vault_ref": s.get("vault_ref"), "secret_type": s.get("secret_type")}
                    for s in sd.get("credentials_or_secrets", [])
                ]
            # Remove source absolute paths
            source = cj.get("source", {})
            source.pop("absolute_path", None)
            doc["canonical_json"] = cj

        # Truncate text for API response
        if doc.get("canonical_text") and len(doc["canonical_text"]) > 50000:
            doc["canonical_text"] = doc["canonical_text"][:50000] + "\n\n[TRUNCATED]"

        return doc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Jobs ──────────────────────────────────────────────────────

@router.get("/api/digitalization/jobs")
def digitalization_jobs(limit: int = Query(20, ge=1, le=100)) -> dict:
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, provider, status, started_at, finished_at,
                           total_files, processed_files, failed_files, dry_run, created_by
                    FROM platform.digitalization_job
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (limit,))
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                # Sanitize root_path
                for r in rows:
                    r.pop("root_path", None)
        return {"jobs": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/digitalization/jobs/{job_id}")
def digitalization_job_detail(job_id: str) -> dict:
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, provider, status, started_at, finished_at,
                           total_files, processed_files, failed_files, dry_run,
                           error_summary, created_by
                    FROM platform.digitalization_job WHERE id = %s;
                """, (job_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Job not found")
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Chunks ────────────────────────────────────────────────────

@router.get("/api/digitalization/chunks/{document_id}")
def digitalization_chunks(document_id: str, limit: int = Query(50, ge=1, le=200)) -> dict:
    """Return chunks for a document — no secrets."""
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT dc.chunk_id, dc.chunk_index, dc.text, dc.metadata, dc.token_count, dc.embedding_status
                    FROM platform.document_chunk dc
                    JOIN platform.canonical_document cd ON cd.id = dc.canonical_document_id
                    WHERE cd.document_id = %s
                    ORDER BY dc.chunk_index
                    LIMIT %s;
                """, (document_id, limit))
                cols = [d[0] for d in cur.description]
                chunks = [dict(zip(cols, r)) for r in cur.fetchall()]

        # Sanitize metadata paths
        for c in chunks:
            meta = c.get("metadata")
            if isinstance(meta, str):
                meta = json.loads(meta)
            if isinstance(meta, dict):
                meta.pop("absolute_path", None)
                meta["logical_path"] = _safe_path(meta.get("logical_path", ""))
                c["metadata"] = meta

        return {"document_id": document_id, "chunks": chunks, "count": len(chunks)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── OCR retry ─────────────────────────────────────────────────

@router.post("/api/digitalization/ocr/retry/{document_id}")
def digitalization_ocr_retry(document_id: str, user: dict = Depends(require_admin_user)) -> dict:
    """Re-queue OCR for a scanned document (admin)."""
    from app_skeleton.api.ocr.queue import requeue_ocr_for_document

    try:
        with psycopg.connect(_db_conn(), connect_timeout=10) as conn:
            result = requeue_ocr_for_document(conn, document_id)
            conn.commit()
        return {"status": "ok", **result}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("OCR retry failed for %s", document_id)
        raise HTTPException(status_code=500, detail=str(exc)[:300]) from exc
