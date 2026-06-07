"""Document library explorer API."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response

from app_skeleton.api import document_library_service as svc
from app_skeleton.api.library_taxonomy import describe_nav_scope
from app_skeleton.security.auth import require_platform_user

router = APIRouter()


@router.get("/api/document-library/taxonomy")
def document_library_taxonomy(user: dict = Depends(require_platform_user)) -> dict[str, Any]:
    taxonomy = svc.get_library_taxonomy()
    example = describe_nav_scope("wet_lab", "protocols")
    taxonomy["nav_scope_help"] = {
        "description": "Map sidebar main_id/sub_id to domain_tab + filter fields for scoped search.",
        "example": example,
        "endpoint": "/api/document-library/nav-scope/{main_id}/{sub_id}",
    }
    return taxonomy


@router.get("/api/document-library/nav-scope/{main_id}/{sub_id}")
def document_library_nav_scope(
    main_id: str,
    sub_id: str,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    scope = describe_nav_scope(main_id, sub_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Unknown navigation scope")
    return scope


@router.get("/api/document-library/stats")
def document_library_stats(user: dict = Depends(require_platform_user)) -> dict[str, Any]:
    return svc.get_stats()


@router.get("/api/document-library/search")
def document_library_search(
    q: str = Query("", description="Global search query"),
    domain_tab: Optional[str] = Query(None, description="overview|wet_lab|orders|projects|all_files"),
    system_view: Optional[str] = Query(None, description="Smart system view id"),
    domain: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    digitalization_status: Optional[str] = Query(None),
    preview_status: Optional[str] = Query(None),
    duplicate_status: Optional[str] = Query(None),
    unknown_type: Optional[bool] = Query(None),
    project: Optional[str] = Query(None),
    assay: Optional[str] = Query(None),
    tissue: Optional[str] = Query(None),
    marker: Optional[str] = Query(None),
    protocol_only: Optional[bool] = Query(None),
    protocol_category: Optional[str] = Query(None),
    reagents_only: Optional[bool] = Query(None),
    reagent_category: Optional[str] = Query(None),
    exclude_cycif: Optional[bool] = Query(None),
    cycif_only: Optional[bool] = Query(None),
    app_page: Optional[str] = Query(None),
    smart_chip: Optional[str] = Query(None),
    modified_after: Optional[str] = Query(None),
    modified_before: Optional[str] = Query(None),
    sort: str = Query("filename"),
    order: str = Query("asc"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=5000),
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    filters = {
        k: v
        for k, v in {
            "domain": domain,
            "section": section,
            "category": category,
            "subcategory": subcategory,
            "file_type": file_type,
            "digitalization_status": digitalization_status,
            "preview_status": preview_status,
            "duplicate_status": duplicate_status,
            "unknown_type": unknown_type,
            "project": project,
            "assay": assay,
            "tissue": tissue,
            "marker": marker,
            "protocol_only": protocol_only,
            "protocol_category": protocol_category,
            "reagents_only": reagents_only,
            "reagent_category": reagent_category,
            "exclude_cycif": exclude_cycif,
            "cycif_only": cycif_only,
            "app_page": app_page,
            "smart_chip": smart_chip,
            "modified_after": modified_after,
            "modified_before": modified_before,
        }.items()
        if v is not None
    }
    return svc.search_documents(
        q=q,
        domain_tab=domain_tab,
        system_view=system_view,
        filters=filters,
        sort=sort,
        order=order,
        offset=offset,
        limit=limit,
    )


@router.get("/api/document-library/facets")
def document_library_facets(
    q: str = Query(""),
    domain_tab: Optional[str] = Query(None),
    system_view: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    digitalization_status: Optional[str] = Query(None),
    preview_status: Optional[str] = Query(None),
    duplicate_status: Optional[str] = Query(None),
    unknown_type: Optional[bool] = Query(None),
    project: Optional[str] = Query(None),
    assay: Optional[str] = Query(None),
    tissue: Optional[str] = Query(None),
    marker: Optional[str] = Query(None),
    protocol_only: Optional[bool] = Query(None),
    protocol_category: Optional[str] = Query(None),
    reagents_only: Optional[bool] = Query(None),
    reagent_category: Optional[str] = Query(None),
    exclude_cycif: Optional[bool] = Query(None),
    cycif_only: Optional[bool] = Query(None),
    app_page: Optional[str] = Query(None),
    smart_chip: Optional[str] = Query(None),
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    filters = {
        k: v
        for k, v in {
            "domain": domain,
            "section": section,
            "category": category,
            "subcategory": subcategory,
            "file_type": file_type,
            "digitalization_status": digitalization_status,
            "preview_status": preview_status,
            "duplicate_status": duplicate_status,
            "unknown_type": unknown_type,
            "project": project,
            "assay": assay,
            "tissue": tissue,
            "marker": marker,
            "protocol_only": protocol_only,
            "protocol_category": protocol_category,
            "reagents_only": reagents_only,
            "reagent_category": reagent_category,
            "exclude_cycif": exclude_cycif,
            "cycif_only": cycif_only,
            "app_page": app_page,
            "smart_chip": smart_chip,
        }.items()
        if v is not None
    }
    return svc.compute_facets(q=q, domain_tab=domain_tab, system_view=system_view, filters=filters)


@router.get("/api/document-library/preview/{asset_id}")
def document_library_preview(
    asset_id: str,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    preview = svc.get_preview(asset_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Asset not found")
    return preview


@router.get("/api/document-library/category-trees")
def document_library_category_trees(
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    return svc.load_category_trees()


@router.get("/api/document-library/export/{asset_id}/formats")
def document_export_formats(
    asset_id: str,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    payload = svc.get_export_formats(asset_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Asset not found")
    return payload


@router.get("/api/document-library/export/{asset_id}")
def document_export(
    asset_id: str,
    format: str = Query("original", description="original|txt|md|json|csv"),
    user: dict = Depends(require_platform_user),
):
    result = svc.export_document(asset_id, format)
    if not result:
        raise HTTPException(status_code=404, detail="Export unavailable for this format")
    if result.get("kind") == "file":
        return FileResponse(
            path=result["path"],
            filename=result["filename"],
            media_type=result["media_type"],
        )
    return Response(
        content=result["content"],
        media_type=result["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )
