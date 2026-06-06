from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app_skeleton.security.auth import require_platform_user
from app_skeleton.security.permissions import require_role

LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/api/research-knowledge", tags=["research-knowledge"])

@router.get("/status")
def research_knowledge_status(user: dict = Depends(require_platform_user)) -> dict:
    """Return high-level source/index health. Wire this to DB and Qdrant in production."""
    return {
        "status": "scaffold",
        "collection": "research_knowledge",
        "vector_name": "text",
        "message": "Connect this route to ResearchKnowledgeStatus and Qdrant health checks.",
    }

@router.post("/crawl/farkkila")
def crawl_farkkila_site(max_pages: int = Query(50, ge=1, le=300), user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    from app_skeleton.api.research_crawler import crawl_seed_urls
    seeds = [
        "https://www.farkkilab.org/",
        "https://www.farkkilab.org/research",
        "https://www.farkkilab.org/publications",
        "https://www.farkkilab.org/clinic",
        "https://www.farkkilab.org/news",
    ]
    pages = crawl_seed_urls(seeds, max_pages=max_pages)
    # TODO: persist source/document/chunks, extract entities, index Qdrant.
    return {"status": "crawled", "page_count": len(pages), "pages": [p.__dict__ for p in pages[:10]]}

@router.post("/ingest-publications")
def ingest_publications(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    from app_skeleton.api.publication_fetcher import discover_priority_publications
    records = discover_priority_publications()
    # TODO: persist and index.
    return {"status": "discovered", "count": len(records), "records": records[:20]}

@router.get("/search")
def research_knowledge_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=80),
    user: dict = Depends(require_platform_user),
) -> dict:
    # TODO: call Qdrant + PostgreSQL + knowledge graph search.
    return {"query": q, "count": 0, "hits": [], "warning": "Scaffold route. Connect to research_search_service."}
