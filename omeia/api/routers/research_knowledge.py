"""Research knowledge base API — crawl, ingest, search, status."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from omeia.api.common import llm_client, qdrant_client
from omeia.api.publication_fetcher import discover_priority_publications
from omeia.api.research_knowledge_models import ResearchKnowledgeStatus
from omeia.api.research_knowledge_store import (
    crawl_farkkila_seeds,
    get_status,
    ingest_publications,
    search_research,
    seed_datasets,
)
from omeia.security.auth import require_platform_user
from omeia.security.permissions import require_role

LOGGER = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/research-knowledge/status", response_model=ResearchKnowledgeStatus)
def research_knowledge_status(user: dict = Depends(require_platform_user)) -> ResearchKnowledgeStatus:
    return get_status(qdrant=qdrant_client)


@router.post("/api/research-knowledge/crawl/farkkila")
def crawl_farkkila_site(
    max_pages: int = Query(50, ge=1, le=300),
    user: dict = Depends(require_platform_user),
) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        return crawl_farkkila_seeds(max_pages=max_pages, qdrant=qdrant_client, llm=llm_client)
    except Exception as exc:
        LOGGER.exception("Färkkilä crawl failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/research-knowledge/ingest-publications")
def ingest_publications_route(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    records = discover_priority_publications()
    try:
        result = ingest_publications(records, qdrant=qdrant_client, llm=llm_client)
        return {"status": "ingested", **result}
    except Exception as exc:
        LOGGER.exception("Publication ingest failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/research-knowledge/seed-datasets")
def seed_datasets_route(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        return seed_datasets(qdrant=qdrant_client, llm=llm_client)
    except Exception as exc:
        LOGGER.exception("Dataset seed failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/research-knowledge/search")
def research_knowledge_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=80),
    user: dict = Depends(require_platform_user),
) -> dict:
    return search_research(q, limit=limit, qdrant=qdrant_client, llm=llm_client)
