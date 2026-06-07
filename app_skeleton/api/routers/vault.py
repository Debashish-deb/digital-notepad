from app_skeleton.security.permissions import require_role
from app_skeleton.security.auth import require_platform_user
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from app_skeleton.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

@router.post("/ingest-document")
def ingest_document(req: DocumentIngestRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        email = user.get("email")
        uid = user.get("uid") or user.get("sub")
        
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Find researcher ID securely by mapping Firebase email/uid to username
                # platform.researcher only has a 'username' column, so we match against email prefix or uid
                username_guess = email.split("@")[0] if email else uid
                cur.execute("""
                    SELECT researcher_id FROM platform.researcher 
                    WHERE username = %s OR username = %s LIMIT 1;
                """, (username_guess, email))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=403, detail="No researcher profile linked to this authenticated user.")
                rid = row[0]

                # Find project ID if project_code is provided
                pid = None
                if req.project_code:
                    cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                    row = cur.fetchone()
                    if row:
                        pid = row[0]

                # 1. Chunking and Embedding
                text = req.extracted_text or ""
                chunk_size = 3500
                overlap = 500
                chunks = []
                start = 0
                while start < len(text):
                    end = start + chunk_size
                    chunk = text[start:end]
                    if chunk.strip():
                        chunks.append(chunk.strip())
                    start += chunk_size - overlap
                
                # We use the existing LLMClient to embed locally without secrets if offline
                active_llm = LLMClient()
                points = []
                import hashlib
                import uuid
                
                from app_skeleton.api.qdrant_vectors import (
                    DOC_CHUNKS_COLLECTION,
                    stable_point_uuid,
                    upsert_text_points,
                )

                for idx, chunk in enumerate(chunks):
                    vec = active_llm.embed(chunk, dim=384)
                    text_hash = hashlib.md5(chunk.encode("utf-8")).hexdigest()
                    point_id_str = f"ingest_{req.filename}_{idx}_{text_hash}"
                    point_uuid = stable_point_uuid(point_id_str)

                    points.append(models.PointStruct(
                        id=point_uuid,
                        vector={ "text": vec },
                        payload={
                            "corpus": "project_workspace",
                            "project_code": req.project_code,
                            "researcher_id": str(rid),
                            "filename": req.filename,
                            "title": req.filename,
                            "document_title": req.filename,
                            "chunk_index": idx,
                            "chunk_id": str(idx),
                            "text": chunk,
                            "text_preview": chunk[:2000],
                            "text_hash": text_hash,
                            "source_type": "ingested_document",
                        }
                    ))

                qdrant_indexed = 0
                if points:
                    try:
                        qdrant_indexed = upsert_text_points(
                            qdrant_client, points, collection=DOC_CHUNKS_COLLECTION
                        )
                    except Exception as qc_err:
                        LOGGER.warning(
                            "Qdrant ingest skipped (offline stub — document stored in Postgres only): %s",
                            qc_err,
                        )

                # 2. Insert document record tracking the indexing
                cur.execute("""
                    INSERT INTO platform.document_ingestion (filename, file_type, extracted_text, tags, project_id, software_associations, pipeline_stage_associations, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING doc_id;
                """, (req.filename, req.file_type, req.extracted_text, req.tags, pid, req.software_associations, req.pipeline_stage_associations, psycopg.types.json.Jsonb(req.metadata_dict)))
                doc_id = cur.fetchone()[0]

                # Update the payload with actual doc_id now that we have it (optional, we already indexed)
                # But it's fine, we used project_code and filename in Qdrant

                # Log into Digital Notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Document Indexed: {req.filename}",
                    content=f"Document '{req.filename}' ({req.file_type}) indexed.\nQdrant chunks: {qdrant_indexed}/{len(points)}\nAssociations:\n- Software: {', '.join(req.software_associations) or 'None'}",
                    entry_type="general_note"
                )

                conn.commit()
                return {
                    "status": "success",
                    "doc_id": str(doc_id),
                    "chunks_indexed": len(points),
                    "qdrant_indexed": qdrant_indexed,
                }
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/gap-analysis")
def gap_analysis() -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # 1. Total projects count
                cur.execute("SELECT COUNT(*) FROM core.project;")
                total_projects = cur.fetchone()[0]

                # 2. Checklist stats
                cur.execute("SELECT COUNT(*), SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) FROM platform.onboarding_checklist;")
                total_items, completed_items = cur.fetchone()
                total_items = total_items or 0
                completed_items = completed_items or 0
                readiness_score = round((completed_items / total_items * 100), 1) if total_items > 0 else 0.0

                # 3. Project-specific scores
                cur.execute("""
                    SELECT p.project_code, p.project_name, COUNT(c.checklist_id), SUM(CASE WHEN c.status = 'completed' THEN 1 ELSE 0 END)
                    FROM core.project p
                    LEFT JOIN platform.onboarding_checklist c ON p.project_id = c.project_id
                    GROUP BY p.project_code, p.project_name
                    ORDER BY p.project_code;
                """)
                project_breakdown = []
                for code, name, t_count, c_count in cur.fetchall():
                    t_count = t_count or 0
                    c_count = c_count or 0
                    p_score = round((c_count / t_count * 100), 1) if t_count > 0 else 0.0
                    project_breakdown.append({
                        "project_code": code,
                        "project_name": name,
                        "total_items": t_count,
                        "completed_items": c_count,
                        "score": p_score
                    })

                # 4. Inventory counts
                cur.execute("SELECT COUNT(*) FROM platform.ai_model;")
                ai_models_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.infrastructure;")
                infrastructure_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.publication;")
                publications_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.document_ingestion;")
                documents_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.folder_catalog;")
                folders_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.dataset_catalog;")
                datasets_count = cur.fetchone()[0]

                # Find missing items
                cur.execute("""
                    SELECT p.project_code, c.category, c.item_name
                    FROM platform.onboarding_checklist c
                    JOIN core.project p ON c.project_id = p.project_id
                    WHERE c.status = 'pending'
                    ORDER BY p.project_code, c.category
                    LIMIT 20;
                """)
                missing_checklist_items = [{"project_code": r[0], "category": r[1], "item_name": r[2]} for r in cur.fetchall()]

                # Generate dynamic recommendations
                recommendations = []
                if readiness_score < 50:
                    recommendations.append("Priority 1: Populate pending checklist items for active clinical cohorts (stitching runs & segmented cell masks).")
                if publications_count == 0:
                    recommendations.append("Priority 2: Seed the publication registry with lab papers to facilitate citation references for Chat Copilot.")
                if documents_count < 5:
                    recommendations.append("Priority 3: Utilize the Document Ingestion wizard to upload local multiplex staining protocols and Slurm template scripts.")
                if ai_models_count < 10:
                    recommendations.append("Priority 4: Verify the local installation scripts for segmentation models (Mesmer / SAM2) are registered.")
                
                if not recommendations:
                    recommendations.append("All core metadata fields are populated. Ready to scale to production multi-cohort processing.")

                coverage = project_catalog_coverage()

                return {
                    "total_projects": total_projects,
                    "catalog_coverage": coverage,
                    "readiness_score": readiness_score,
                    "completed_checklist_items": completed_items,
                    "total_checklist_items": total_items,
                    "project_breakdown": project_breakdown,
                    "ai_models_count": ai_models_count,
                    "infrastructure_count": infrastructure_count,
                    "publications_count": publications_count,
                    "documents_count": documents_count,
                    "folders_count": folders_count,
                    "datasets_count": datasets_count,
                    "missing_checklist_items": missing_checklist_items,
                    "recommendations": recommendations
                }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/api/vault/summary", dependencies=_FIREBASE_PROTECTED)
def vault_summary_endpoint() -> dict:
    summary = vault_summary()
    public = {k: v for k, v in summary.items() if k != "database_root"}
    missing = assert_all_section_roots_exist()
    return {"summary": public, "missing_section_roots": missing}

@router.get("/api/vault/search", dependencies=_FIREBASE_PROTECTED)
def vault_search(
    q: str = Query("", min_length=0),
    domain: Optional[str] = Query(None),
    project_hint: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    extraction_status: Optional[str] = Query(None),
    vector_status: Optional[str] = Query(None),
    uncategorized_only: bool = Query(False),
    limit: int = Query(25, ge=1, le=100),
) -> dict:
    results = search_vault(
        q,
        domain=domain,
        project_hint=project_hint,
        review_status=review_status,
        extraction_status=extraction_status,
        vector_status=vector_status,
        uncategorized_only=uncategorized_only,
        limit=limit,
    )
    return {"query": q, "count": len(results), "results": results}

@router.get("/api/vault/review-queue", dependencies=_FIREBASE_PROTECTED)
def vault_review_queue_endpoint(
    limit: int = Query(50, ge=1, le=200),
    max_confidence: float = Query(0.85, ge=0, le=1),
    queue: str = Query("low_confidence", description="low_confidence | uncategorized | failed"),
    extraction_status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
) -> dict:
    rows = vault_review_queue(
        limit=limit,
        max_confidence=max_confidence,
        queue=queue,
        extraction_status=extraction_status,
        review_status=review_status,
    )
    return {"count": len(rows), "queue": queue, "items": rows}

@router.patch("/api/vault/review/{asset_id}", dependencies=_FIREBASE_PROTECTED)
def vault_mark_reviewed(
    asset_id: str,
    review_status: str = Query("reviewed"),
) -> dict:
    return mark_asset_reviewed(asset_id, review_status=review_status)

@router.post("/api/vault/ingest/scan", dependencies=_FIREBASE_PROTECTED)
def vault_ingest_scan(
    resume: bool = Query(False),
    confirm_full_scan: bool = Query(False, description="Required for full DATABASE_ROOT scan (safety)"),
) -> dict:
    job = platform_admin.create_ingestion_job("vault_ingest_scan", config={"resume": resume})
    if not confirm_full_scan:
        raise HTTPException(
            status_code=400,
            detail="Set confirm_full_scan=true to run a full vault scan (read-only, metadata writes only).",
        )
    try:
        result = run_ingest_scan(resume=resume, job_id=str(job["job_id"]))
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("counts", {}).get("scanned"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault ingest scan failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/vault/ingest/project/{project_id}", dependencies=_FIREBASE_PROTECTED)
def vault_ingest_project_endpoint(
    project_id: str,
    resume: bool = Query(False),
) -> dict:
    job = platform_admin.create_ingestion_job(
        "vault_ingest_project",
        config={"project_id": project_id, "resume": resume},
    )
    try:
        result = vault_ingest_project(project_id, resume=resume, job_id=str(job["job_id"]))
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("counts", {}).get("scanned"),
        )
        return {**result, "job_id": job["job_id"]}
    except FileNotFoundError as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault project ingest failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/digitalize/scan", dependencies=_FIREBASE_PROTECTED)
def digitalize_scan(
    dry_run: bool = Query(False),
    resume: bool = Query(False),
    max_files: Optional[int] = Query(None, ge=1, le=100000),
) -> dict:
    from app_skeleton.api.project_digitalization_engine import run_digitalization

    try:
        return run_digitalization(mode="full", resume=resume, dry_run=dry_run, max_files=max_files)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/api/digitalize/project/{project_name}", dependencies=_FIREBASE_PROTECTED)
def digitalize_project(
    project_name: str,
    resume: bool = Query(False),
    dry_run: bool = Query(False),
    max_files: Optional[int] = Query(None, ge=1, le=100000),
) -> dict:
    from app_skeleton.api.project_digitalization_engine import run_digitalization

    try:
        return run_digitalization(
            mode="project",
            project_name=project_name,
            resume=resume,
            dry_run=dry_run,
            max_files=max_files,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post("/api/digitalize/retry-failed", dependencies=_FIREBASE_PROTECTED)
def digitalize_retry_failed(
    project_name: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
) -> dict:
    from app_skeleton.api.vault_ingestion_engine import retry_failed_extractions

    return retry_failed_extractions(project_hint=project_name, limit=limit)

@router.get("/api/digitalize/search", dependencies=_FIREBASE_PROTECTED)
def digitalize_search(
    q: str = Query(..., min_length=1),
    uncategorized_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    from app_skeleton.api.project_digitalization_engine import search_knowledge

    return {"items": search_knowledge(q, uncategorized_only=uncategorized_only, limit=limit)}

@router.get("/api/digitalize/review", dependencies=_FIREBASE_PROTECTED)
def digitalize_review(
    kind: str = Query("uncategorized"),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    from app_skeleton.api.project_digitalization_engine import list_review_queue

    return {"kind": kind, "items": list_review_queue(kind=kind, limit=limit)}

@router.patch("/api/digitalize/review/{asset_id}", dependencies=_FIREBASE_PROTECTED)
def digitalize_patch_review(
    asset_id: str,
    user_category: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    project_candidate_id: Optional[str] = Query(None),
) -> dict:
    from app_skeleton.api.project_digitalization_engine import patch_asset_review

    return patch_asset_review(
        asset_id,
        user_category=user_category,
        review_status=review_status,
        project_candidate_id=project_candidate_id,
    )

@router.get("/api/digitalize/runs", dependencies=_FIREBASE_PROTECTED)
def digitalize_runs(limit: int = Query(20, ge=1, le=100)) -> dict:
    from app_skeleton.api.project_digitalization_engine import _db_conn
    import psycopg

    with psycopg.connect(_db_conn(), connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT run_id, mode, storage_root, project_name, status, dry_run, started_at, finished_at
                FROM platform.digitalization_runs
                ORDER BY started_at DESC LIMIT %s;
                """,
                (limit,),
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"runs": rows}

@router.post("/api/vault/ingest/retry-failed", dependencies=_FIREBASE_PROTECTED)
def vault_ingest_retry_failed(
    project_hint: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
) -> dict:
    job = platform_admin.create_ingestion_job(
        "vault_ingest_retry_failed",
        config={"project_hint": project_hint, "limit": limit},
    )
    try:
        result = retry_failed_extractions(
            project_hint=project_hint,
            limit=limit,
            job_id=str(job["job_id"]),
        )
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("counts", {}).get("retried"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault retry-failed failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/vault/rebuild", dependencies=_FIREBASE_PROTECTED)
def vault_rebuild(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    job = platform_admin.create_ingestion_job("vault_rebuild")
    try:
        result = vault_rebuild_inventory()
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("asset_count") or result.get("count"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault rebuild failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/supabase/sync/documents", dependencies=_FIREBASE_PROTECTED)
def supabase_sync_documents(
    dry_run: bool = Query(False),
    limit: Optional[int] = Query(None, ge=1, le=10_000),
    since: Optional[str] = Query(None, description="ISO timestamp for vault.updated_at filter"),
    _admin: dict = Depends(require_admin),
) -> dict:
    """Sync document metadata + truncated text from local Postgres to hosted Supabase (admin)."""
    del _admin
    job = platform_admin.create_ingestion_job(
        "supabase_document_sync",
        config={"dry_run": dry_run, "limit": limit, "since": since},
    )
    try:
        result = sync_documents_to_supabase(dry_run=dry_run, limit=limit, since=since)
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("document_rows_synced") or result.get("would_sync"),
            error_summary=None if result.get("status") in ("ok", "dry_run") else result.get("message"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Supabase document sync failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/vault/sync", dependencies=_FIREBASE_PROTECTED)
def vault_sync_postgres(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Phase 3: upsert JSON inventory into platform.raw_asset_vault."""
    job = platform_admin.create_ingestion_job("vault_sync")
    try:
        result = sync_inventory_to_postgres()
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("upserted") or result.get("postgres_rows"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault sync failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/api/vault/dedupe-report", dependencies=_FIREBASE_PROTECTED)
def vault_dedupe_report(limit: int = Query(30, ge=1, le=100)) -> dict:
    return deduplication_report(limit=limit)

@router.get("/api/vault/manifest", dependencies=_FIREBASE_PROTECTED)
def vault_manifest(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    return vault_manifest_page(offset=offset, limit=limit)

@router.get("/api/vault/scheduled-scan/status", dependencies=_FIREBASE_PROTECTED)
def vault_scheduled_scan_status(user: dict = Depends(require_platform_user)) -> dict:
    from app_skeleton.api.scheduled_directory_scanner import scheduled_directory_scanner
    return scheduled_directory_scanner.status()

@router.post("/api/vault/scheduled-scan/run", dependencies=_FIREBASE_PROTECTED)
def vault_scheduled_scan_run(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    from app_skeleton.api.scheduled_directory_scanner import scheduled_directory_scanner
    if scheduled_directory_scanner.is_running:
        raise HTTPException(status_code=409, detail="Scheduled scan already running")
    return scheduled_directory_scanner.run_scan(reason="api")

@router.get("/api/supabase/sync/status")
def supabase_sync_status_endpoint() -> dict:
    """Last Supabase document sync report (no secrets)."""
    status = supabase_sync_status()
    last_report = read_last_sync_report()
    return {"status": status, "last_report": last_report}