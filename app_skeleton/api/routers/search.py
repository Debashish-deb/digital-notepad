"""Unified platform search API."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app_skeleton.api.common import DB_CONN, llm_client, qdrant_client
from app_skeleton.api.search_models import SearchMode, SearchSuggestionsResponse, UnifiedSearchResponse
from app_skeleton.api.search_service import SearchService
from app_skeleton.security.auth import require_platform_user

router = APIRouter()


def _search_service() -> SearchService:
    return SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=llm_client)


@router.get("/api/platform/unified-search", response_model=UnifiedSearchResponse)
def platform_unified_search(
    q: str = Query(..., min_length=2),
    scopes: Optional[str] = Query(
        None,
        description="Comma-separated: lab,file,vault,notebook,wiki,decision,task,project",
    ),
    project_code: Optional[str] = Query(None),
    project_codes: Optional[str] = Query(None, description="Comma-separated project codes"),
    section_id: Optional[str] = Query(None),
    page_domain_id: Optional[str] = Query(None),
    mode: SearchMode = Query("hybrid"),
    limit: int = Query(25, ge=1, le=50),
    offset: int = Query(0, ge=0, le=500),
    include_restricted: bool = Query(False),
    explain: bool = Query(False),
    user: dict = Depends(require_platform_user),
) -> UnifiedSearchResponse:
    """Canonical omnibox search — semantic + keyword + metadata across lab corpora."""
    try:
        return _search_service().unified_search(
            q,
            scopes=scopes,
            project_code=project_code,
            project_codes=project_codes,
            section_id=section_id,
            page_domain_id=page_domain_id,
            mode=mode,
            limit=limit,
            offset=offset,
            include_restricted=include_restricted,
            explain=explain,
            user_role=user.get("role"),
            user_email=user.get("email"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/platform/search-suggestions", response_model=SearchSuggestionsResponse)
def platform_search_suggestions(
    q: str = Query("", max_length=200),
    limit: int = Query(8, ge=1, le=20),
    user: dict = Depends(require_platform_user),
) -> SearchSuggestionsResponse:
    """Prefix suggestions, synonym hints, and recent logged queries."""
    data = _search_service().search_suggestions(q, user_email=user.get("email"), limit=limit)
    return SearchSuggestionsResponse(**data)


@router.get("/api/platform/search-index-status")
def platform_search_index_status(
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    """Index freshness for admin/dev — portable stub + Qdrant + Postgres status."""
    return _search_service().index_status()


@router.get("/api/project-files/search")
def project_files_search(
    q: str = Query(..., min_length=2),
    project_code: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    """Search processed project workspace twins (portable JSON index)."""
    svc = _search_service()
    codes = project_code or None
    hits = svc.search_project_files(q, project_code=codes, limit=limit)
    return {"query": q, "project_code": project_code, "count": len(hits), "hits": [h.model_dump() for h in hits]}
