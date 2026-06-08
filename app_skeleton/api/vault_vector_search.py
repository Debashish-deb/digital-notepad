"""Semantic search over vault_asset_chunks Qdrant collection."""
from __future__ import annotations

import logging
import os
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app_skeleton.api.embedding_service import embed_text
from app_skeleton.api.qdrant_collections import VAULT_CHUNKS
from app_skeleton.api.qdrant_vectors import TEXT_VECTOR_NAME, ensure_named_text_collection, get_qdrant_client

LOGGER = logging.getLogger(__name__)


def vectorization_enabled() -> bool:
    return (os.getenv("VECTORIZATION_ENABLED", "false") or "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def search_vault_vectors(
    query: str,
    *,
    limit: int = 25,
    qdrant: QdrantClient | None = None,
    llm: Any | None = None,
) -> list[dict[str, Any]]:
    """Semantic search on vault_asset_chunks; returns empty when VECTORIZATION_ENABLED=false."""
    if not vectorization_enabled():
        return []
    query = (query or "").strip()
    if len(query) < 2:
        return []

    limit = max(1, min(int(limit or 25), 100))
    try:
        client = qdrant or get_qdrant_client()
        ensure_named_text_collection(client, VAULT_CHUNKS)
        vector = embed_text(query, llm=llm)
        result = client.query_points(
            collection_name=VAULT_CHUNKS,
            query=vector,
            using=TEXT_VECTOR_NAME,
            limit=limit,
        )
        hits: list[dict[str, Any]] = []
        for point in getattr(result, "points", []) or []:
            payload = point.payload or {}
            hits.append({
                "asset_id": payload.get("asset_id") or str(point.id),
                "score": float(point.score or 0.0),
                "filename": payload.get("filename"),
                "logical_path": payload.get("logical_path"),
                "excerpt": str(payload.get("text") or payload.get("text_preview") or "")[:1200],
                "metadata": payload,
            })
        return hits
    except Exception as exc:
        LOGGER.warning("Vault vector search failed: %s", exc)
        return []
