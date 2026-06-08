"""Ranked retrieval of lab knowledge for chat/search integration."""
from __future__ import annotations

import logging
from typing import Any

from omeia.api.confidence_scorer import retrieval_warning_for_status, score_knowledge_for_retrieval
from omeia.api.learning_models import LearningRetrievalHit, StorageStatus
from omeia.api.learning_store import list_graph_edges, schema_available, search_knowledge
from omeia.api.search_models import SearchHit, SearchNavAction

LOGGER = logging.getLogger(__name__)

_RETRIEVAL_ORDER = (
    StorageStatus.VERIFIED.value,
    StorageStatus.DRAFT.value,
    StorageStatus.LOW_CONFIDENCE.value,
)


def retrieve_lab_knowledge(
    query: str,
    *,
    limit: int = 6,
) -> list[LearningRetrievalHit]:
    """Prefer verified lab knowledge; never return rejected."""
    if not schema_available():
        return []

    items = search_knowledge(
        query,
        status_filter=list(_RETRIEVAL_ORDER),
        limit=limit * 3,
        exclude_rejected=True,
    )
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        score = score_knowledge_for_retrieval(item)
        if score < 0:
            continue
        ranked.append((score, item))

    ranked.sort(key=lambda x: x[0], reverse=True)
    hits: list[LearningRetrievalHit] = []
    for score, item in ranked[:limit]:
        status = StorageStatus(item.get("storage_status") or StorageStatus.DRAFT.value)
        hits.append(LearningRetrievalHit(
            knowledge_id=str(item.get("knowledge_id")),
            title=item.get("title") or "Lab knowledge",
            content=(item.get("content") or "")[:600],
            storage_status=status,
            confidence_score=float(item.get("confidence_score") or 0.0),
            has_citation=bool(item.get("has_citation")),
            score=score,
            warning=retrieval_warning_for_status(status),
            metadata={
                "entity_type": item.get("entity_type"),
                "classification": item.get("classification"),
                "version": item.get("version"),
            },
        ))
    return hits


def learning_hits_to_search_hits(learning_hits: list[LearningRetrievalHit]) -> list[SearchHit]:
    """Convert learning retrieval hits into SearchHit for copilot merge."""
    search_hits: list[SearchHit] = []
    for idx, hit in enumerate(learning_hits):
        search_hits.append(SearchHit(
            id=f"lab_knowledge:{hit.knowledge_id}",
            bucket="lab",
            title=hit.title,
            snippet=hit.content[:400],
            score=hit.score,
            rank=idx + 1,
            source="continuous_learning",
            source_type="lab_knowledge",
            document_code=hit.knowledge_id,
            metadata={
                "storage_status": hit.storage_status.value,
                "confidence_score": hit.confidence_score,
                "has_citation": hit.has_citation,
                "learning_warning": hit.warning,
                "retrieval_tier": "verified_lab_knowledge" if hit.storage_status == StorageStatus.VERIFIED else "draft_lab_knowledge",
            },
            nav=SearchNavAction(
                action="open_learning_knowledge",
                label="View lab knowledge",
                payload={"knowledge_id": hit.knowledge_id},
            ),
        ))
    return search_hits


def retrieve_graph_claims(query: str, *, limit: int = 4) -> list[dict[str, Any]]:
    """Graph-backed claims for secondary retrieval tier."""
    if not schema_available():
        return []
    tokens = query.split()
    subject = tokens[0] if tokens else None
    edges = list_graph_edges(
        subject_name=subject,
        status_filter=[
            StorageStatus.VERIFIED.value,
            StorageStatus.DRAFT.value,
        ],
        limit=limit,
    )
    return edges


def merge_learning_into_copilot_hits(
    query: str,
    base_hits: list[SearchHit],
    *,
    learning_limit: int = 4,
) -> list[SearchHit]:
    """
    Prepend verified lab knowledge, then verified pubs/graph, then base hits.
    Draft items append with warning metadata; rejected never included.
    """
    learning_hits = retrieve_lab_knowledge(query, limit=learning_limit)
    learning_search = learning_hits_to_search_hits(learning_hits)

    seen_ids = {h.id for h in learning_search}
    merged = list(learning_search)

    for hit in base_hits:
        if hit.id in seen_ids:
            continue
        merged.append(hit)
        seen_ids.add(hit.id)

    for idx, hit in enumerate(merged):
        hit.rank = idx + 1
    return merged
