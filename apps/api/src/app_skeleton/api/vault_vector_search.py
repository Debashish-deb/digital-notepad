"""Semantic search over vault_asset_chunks Qdrant collection."""
from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app_skeleton.api.embedding_service import embed_text
from app_skeleton.api.platform_flags import vectorization_enabled
from app_skeleton.api.qdrant_collections import VAULT_CHUNKS
from app_skeleton.api.qdrant_vectors import TEXT_VECTOR_NAME, ensure_named_text_collection, get_qdrant_client
from app_skeleton.api.raw_vault_store import (
    _is_vault_row_active,
    fetch_vault_assets_by_ids,
    vault_postgres_reachable,
)

LOGGER = logging.getLogger(__name__)


def filter_and_enrich_vault_vector_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop inactive/missing vault assets and merge authoritative Postgres fields."""
    if not hits:
        return []

    asset_ids = [str(h.get("asset_id") or "").strip() for h in hits if h.get("asset_id")]
    assets = fetch_vault_assets_by_ids(asset_ids)
    postgres_ok = vault_postgres_reachable()

    enriched: list[dict[str, Any]] = []
    for hit in hits:
        asset_id = str(hit.get("asset_id") or "").strip()
        asset = assets.get(asset_id) if asset_id else None

        if postgres_ok:
            if not asset or not _is_vault_row_active(asset):
                continue
        elif asset and not _is_vault_row_active(asset):
            continue

        out = dict(hit)
        if asset:
            out["filename"] = asset.get("filename") or out.get("filename")
            out["logical_path"] = asset.get("logical_path") or out.get("logical_path")
            out["checksum_sha256"] = asset.get("checksum_sha256") or out.get("checksum_sha256")
            out["review_status"] = asset.get("review_status")
            out["vector_status"] = asset.get("vector_status")
            out["domain"] = asset.get("domain")
            out["project_hint"] = asset.get("project_hint")
            out["page_domain_id"] = asset.get("page_domain_id")
            out["page_section_id"] = asset.get("page_section_id")
            meta = dict(out.get("metadata") or {})
            meta.update({
                "asset_id": asset_id,
                "filename": out.get("filename"),
                "logical_path": out.get("logical_path"),
                "checksum_sha256": out.get("checksum_sha256"),
                "review_status": asset.get("review_status"),
                "vector_status": asset.get("vector_status"),
            })
            out["metadata"] = meta
        enriched.append(out)
    return enriched


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
                "checksum_sha256": payload.get("checksum_sha256"),
                "excerpt": str(payload.get("text") or payload.get("text_preview") or "")[:1200],
                "metadata": payload,
            })
        return filter_and_enrich_vault_vector_hits(hits)
    except Exception as exc:
        LOGGER.warning("Vault vector search failed: %s", exc)
        return []
