from app_skeleton.security.permissions import require_role
from app_skeleton.security.auth import require_platform_user
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from app_skeleton.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

@router.get("/api/database/catalog")
def database_catalog_index() -> dict:
    """Authenticated lab catalog index (replaces public /database/catalog.json)."""
    from app_skeleton.api.lab_catalog_service import build_catalog_index

    return build_catalog_index()


@router.get("/api/database/catalog/docs/{doc_id}")
def database_catalog_document(doc_id: str) -> dict:
    from app_skeleton.api.lab_catalog_service import load_catalog_document

    doc = load_catalog_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.get("/api/database/catalog/document/{doc_id}")
def database_catalog_document_alias(doc_id: str) -> dict:
    return database_catalog_document(doc_id)


@router.get("/api/database/catalog/preview")
def database_catalog_preview_by_path(relative_path: str = Query(..., min_length=1)) -> dict:
    from app_skeleton.api.lab_catalog_service import find_document_by_path

    doc = find_document_by_path(relative_path)
    if not doc:
        raise HTTPException(status_code=404, detail="No extracted preview for this path.")
    return doc


@router.get("/api/database/manifest")
def database_lab_manifest() -> dict:
    from app_skeleton.api.lab_catalog_service import lab_manifest_for_api

    return lab_manifest_for_api()

@router.get("/api/knowledge/lab/stats")
def knowledge_lab_stats() -> dict:
    return get_lab_index_stats()

@router.get("/api/knowledge/lab/search")
def knowledge_lab_search(
    q: str = Query(..., min_length=2),
    section_id: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    if section_id and section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    results = search_lab_knowledge(
        q,
        section_id=section_id,
        limit=limit,
        qdrant=qdrant_client,
        llm=llm_client,
    )
    return {"corpus": LAB_CORPUS, "query": q, "count": len(results), "results": results}

@router.post("/api/knowledge/lab/ingest-all")
def knowledge_lab_ingest_all(req: LabIngestRequest = LabIngestRequest()) -> dict:
    try:
        return ingest_all_lab_sections(
            refresh_extract=req.refresh_extract,
            qdrant=qdrant_client,
            llm=llm_client,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/knowledge/lab/ingest/{section_id}")
def knowledge_lab_ingest_section(section_id: str, req: LabIngestRequest = LabIngestRequest()) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    try:
        return ingest_section_to_database(
            section_id,
            refresh_extract=req.refresh_extract,
            qdrant=qdrant_client,
            llm=llm_client,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/api/knowledge/hybrid-search")
def knowledge_hybrid_search(
    q: str = Query(..., min_length=2),
    section_id: Optional[str] = Query(None),
    limit: int = Query(12, ge=1, le=40),
) -> dict:
    """Semantic lab index + metadata vault search (no disk paths)."""
    lab_hits = search_lab_knowledge(
        q, section_id=section_id, limit=limit, qdrant=qdrant_client, llm=llm_client
    )
    vault_hits = search_vault(q, limit=max(5, limit // 2))
    return {
        "query": q,
        "lab_results": lab_hits,
        "vault_results": vault_hits,
        "count": len(lab_hits) + len(vault_hits),
    }

@router.get("/api/search")
def unified_search(
    response: Response,
    q: str = Query(..., min_length=2),
    mode: str = Query("hybrid"),
    section_id: Optional[str] = Query(None),
    page_domain_id: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    """Unified search: exact|metadata|semantic|hybrid (LUMI-W140).

    Proxies to SearchService.unified_search — legacy response shape preserved.
    """
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/platform/unified-search>; rel="successor-version"'

    mode = (mode or "hybrid").lower()
    scopes: list[str] = []
    if mode in ("semantic", "hybrid"):
        scopes.append("lab")
    if mode in ("metadata", "exact", "hybrid"):
        scopes.append("vault")
    scopes_str = ",".join(scopes) if scopes else "lab,vault"

    from app_skeleton.api.search_service import SearchService

    search_mode = mode if mode in ("keyword", "semantic", "hybrid", "exact") else "hybrid"
    result = SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=llm_client).unified_search(
        q,
        scopes=scopes_str,
        section_id=section_id,
        page_domain_id=page_domain_id,
        mode=search_mode,
        limit=limit,
    )

    lab_results: list[dict] = []
    vault_results: list[dict] = []
    for hit in result.hits:
        if hit.bucket == "lab":
            lab_results.append({
                "rank": hit.rank,
                "score": hit.score,
                "chunk_uid": hit.id,
                "title": hit.title,
                "section_id": hit.section_id,
                "relative_path": hit.relative_path,
                "where_to_find": hit.relative_path,
                "citation": hit.relative_path,
                "excerpt": hit.snippet,
                "source_type": hit.source_type,
            })
        elif hit.bucket == "vault":
            vault_results.append({
                "asset_id": hit.id,
                "filename": hit.title,
                "logical_path": hit.relative_path,
                "metadata_preview": {"excerpt": hit.snippet},
                "page_domain_id": hit.page_domain_id,
                "project_hint": hit.project_code,
                "review_status": (hit.metadata or {}).get("review_status"),
            })

    out: dict = {
        "query": q,
        "mode": mode,
        "lab_results": lab_results,
        "vault_results": vault_results,
        "count": len(lab_results) + len(vault_results),
        "page_domain_id": page_domain_id,
    }
    if mode == "exact" and not out.get("lab_results"):
        out["lab_results"] = []
    return out

@router.get("/api/documents/registry")
def documents_registry(
    section_id: Optional[str] = Query(None),
    corpus: Optional[str] = Query("lab_operations"),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    docs = list_registry_documents(section_id=section_id, corpus=corpus, limit=limit)
    return {"count": len(docs), "documents": docs}

@router.get("/api/lab/sections")
def lab_sections_list(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Lab database sections with processed-twin and vault asset counts.

    Processed twins are read from local ``app_skeleton/data/processed_projects/lab__*.json``
    (not Supabase/remote Postgres). Run ``database_processor --all --refresh`` to rebuild.
    """
    return {
        "sections": list_lab_sections_detail(),
        "missing_section_roots": assert_all_section_roots_exist(),
        "section_count": len(DATABASE_SECTIONS),
        "processed_source": "local_processed_json",
    }

@router.get("/api/lab/section/{section_id}")
def lab_section_detail(section_id: str) -> dict:
    """Processed digital twin for a lab section (local JSON, document preview up to 50)."""
    try:
        return section_detail_for_api(section_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/api/lab/section/{section_id}/summary")
def lab_section_summary(section_id: str) -> dict:
    """Alias for ``GET /api/lab/section/{section_id}`` (backward compatible)."""
    try:
        return section_summary_for_api(section_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/api/lab/section/{section_id}/documents")
def lab_section_documents(
    section_id: str,
    q: Optional[str] = Query(None, min_length=1),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Paginated search within a section's processed document_index (local twin)."""
    try:
        return section_documents_for_api(section_id, q=q, offset=offset, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/api/database/sections")
def database_sections_list() -> dict:
    return {
        "sections": list_sections(),
        "processed_summary": list_processed_summary(),
        "missing_section_roots": assert_all_section_roots_exist(),
    }

@router.get("/api/database/processed-summary")
def database_processed_summary() -> dict:
    return {"sections": list_processed_summary(), "output_dir": str(PROCESSED_DIR)}

@router.get("/api/database/processed/{section_id}")
def database_processed_twin(section_id: str, refresh: bool = False) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    try:
        return get_section_record(section_id, refresh=refresh)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/api/database/processed/{section_id}/summary")
def database_processed_summary(section_id: str) -> dict:
    """Lightweight processed record for UI (document index + metrics, no full chunk text)."""
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    twin = load_processed_section(section_id)
    if not twin:
        raise HTTPException(
            status_code=404,
            detail="Section not processed yet. Run Process all lab database or reprocess_lab_database.py.",
        )
    return {
        "section_id": section_id,
        "section_label": twin.get("section_label"),
        "description": twin.get("description"),
        "metrics": twin.get("metrics"),
        "processed_at": twin.get("processed_at"),
        "extraction": twin.get("extraction"),
        "document_index": twin.get("document_index") or [],
        "folder_tree": (twin.get("folder_tree") or [])[:200],
        "content_library_totals": (twin.get("content_library") or {}).get("totals"),
    }

@router.get("/api/database/processed/{section_id}/document-text")
def database_document_text(
    section_id: str,
    relative_path: str = Query(...),
) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    twin = load_processed_section(section_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Section not processed.")
    norm = relative_path.strip().lstrip("/").replace("\\", "/")
    parts = []
    for chunk in _iter_chunks_from_disk(section_id):
        if (chunk.get("source_file") or "").replace("\\", "/") == norm:
            parts.append((chunk.get("chunk_index") or 0, chunk.get("text") or ""))
    if parts:
        parts.sort(key=lambda x: x[0])
        return {
            "path": norm,
            "content": "\n\n".join(t for _, t in parts if t),
            "source": "processed_chunks",
        }
    for doc in twin.get("document_index") or []:
        if (doc.get("path") or "").replace("\\", "/") == norm and doc.get("excerpt"):
            return {"path": norm, "content": doc["excerpt"], "source": "excerpt"}
    raise HTTPException(status_code=404, detail="No extracted text for this file.")

@router.post("/api/database/process-all")
def database_process_all(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Extract lab files to processed twins, then assimilate into canonical rag.* + Qdrant."""
    job = platform_admin.create_ingestion_job("lab_process_all")
    try:
        extract_result = process_all_sections(refresh=True)
        ingest_result = ingest_all_lab_sections(
            refresh_extract=False,
            qdrant=qdrant_client,
            llm=llm_client,
        )
        totals = ingest_result.get("totals") or {}
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=totals.get("documents") or totals.get("chunks"),
        )
        return {
            "extract": extract_result,
            "ingest": ingest_result,
            "index_stats": get_lab_index_stats(),
            "job_id": job["job_id"],
        }
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/database/process/{section_id}")
def database_process_section(section_id: str, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    try:
        twin = get_section_record(section_id, refresh=True)
        path = save_processed_section(section_id, twin)
        ingest_stats = ingest_section_to_database(
            section_id,
            refresh_extract=False,
            qdrant=qdrant_client,
            llm=llm_client,
        )
        return {
            "section_id": section_id,
            "metrics": twin.get("metrics"),
            "extraction": twin.get("extraction"),
            "output": str(path),
            "ingest": ingest_stats,
            "index_stats": get_lab_index_stats(),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/api/database/search")
def database_search(
    q: str = Query(..., min_length=2),
    section_id: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    """Deprecated alias — routes to canonical lab knowledge search."""
    hits = search_lab_knowledge(q, section_id=section_id, limit=limit)
    source = "lab_knowledge"
    if not hits:
        hits = search_section_chunks(q, section_id=section_id, limit=limit)
        source = "processed_chunks"
    return {"query": q, "count": len(hits), "results": hits, "source": source}

@router.get("/api/database/tree")
def database_tree(
    section_id: str = Query(...),
    relative_path: str = Query(""),
) -> dict:
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)

@router.get("/api/database/read")
def database_read_file(
    section_id: str = Query(...),
    relative_path: str = Query(...),
) -> dict:
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)

@router.get("/api/database/extract")
def database_extract_text(
    section_id: str = Query(...),
    relative_path: str = Query(...),
) -> dict:
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)

@router.get("/api/database/asset")
def database_asset(
    section_id: str = Query(...),
    relative_path: str = Query(...),
):
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)

@router.get("/api/database/asset-url")
def database_asset_url(section_id: str = Query(...), relative_path: str = Query(...)) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    root = section_root(section_id)
    abs_path = safe_relative_path(root, relative_path)
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    if not _is_database_asset_file(abs_path):
        raise HTTPException(status_code=415, detail="File type cannot be opened.")
    return {
        "url": _database_static_url(section_id, relative_path),
        "path": relative_path,
        "section_id": section_id,
        "name": abs_path.name,
        "extension": abs_path.suffix.lower(),
    }