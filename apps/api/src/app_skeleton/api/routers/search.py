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
        description="Comma-separated buckets: lab,file,vault,document_library,vault_review,notebook,wiki,...",
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
    category: Optional[str] = Query(None, description="Document library category filter"),
    smart_chip: Optional[str] = Query(None, description="Document library smart chip filter"),
    domain_tab: Optional[str] = Query(None, description="Document library domain tab filter"),
    system_view: Optional[str] = Query(None, description="Document library system view filter"),
    file_type: Optional[str] = Query(None, description="File type filter (document library / post-filter)"),
    date_from: Optional[str] = Query(None, description="Modified-after date (ISO)"),
    date_to: Optional[str] = Query(None, description="Modified-before date (ISO)"),
    indexed_status: Optional[str] = Query(None, description="indexed | not_indexed"),
    filter_project_codes: Optional[str] = Query(None, description="Advanced filter: comma-separated project codes"),
    filter_section_id: Optional[str] = Query(None, description="Advanced filter: section id"),
    source_buckets: Optional[str] = Query(None, description="Alias for scopes — comma-separated source buckets"),
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
            category=category,
            smart_chip=smart_chip,
            domain_tab=domain_tab,
            system_view=system_view,
            file_type=file_type,
            date_from=date_from,
            date_to=date_to,
            indexed_status=indexed_status,
            filter_project_codes=filter_project_codes,
            filter_section_id=filter_section_id,
            source_buckets=source_buckets,
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
