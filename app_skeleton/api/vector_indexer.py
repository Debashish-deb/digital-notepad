"""Single upsert entry for doc_chunks, research_knowledge, vault_asset_chunks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app_skeleton.api.embedding_service import embed_text, embedding_dim
from app_skeleton.api.qdrant_collections import collection_dim
from app_skeleton.api.qdrant_vectors import (
    TEXT_VECTOR_NAME,
    stable_point_uuid,
    upsert_text_points,
)


@dataclass
class ChunkRecord:
    chunk_uid: str
    chunk_text: str
    document_code: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


def build_point_from_chunk(
    chunk_uid: str,
    text: str,
    payload: dict[str, Any],
    dim: int | None = None,
    *,
    llm: Any | None = None,
) -> models.PointStruct:
    """Build a Qdrant point with embedded text vector."""
    dim = dim or collection_dim()
    vector = embed_text((text or "")[:4000], llm=llm, dim=dim)
    return models.PointStruct(
        id=stable_point_uuid(chunk_uid),
        vector={TEXT_VECTOR_NAME: vector},
        payload={**payload, "chunk_uid": chunk_uid},
    )


def upsert_text_chunks(
    client: QdrantClient,
    points_data: list[dict[str, Any]],
    collection: str | None = None,
    *,
    llm: Any | None = None,
) -> int:
    """Embed and upsert chunk dicts: each item needs chunk_uid, text, payload."""
    if not points_data:
        return 0
    dim = collection_dim()
    points: list[models.PointStruct] = []
    for item in points_data:
        chunk_uid = item.get("chunk_uid") or item.get("chunk_id") or ""
        text = item.get("text") or item.get("chunk_text") or ""
        if not chunk_uid or len(text.strip()) < 8:
            continue
        points.append(
            build_point_from_chunk(
                chunk_uid,
                text,
                item.get("payload") or {},
                dim,
                llm=llm,
            )
        )
    if not points:
        return 0
    return upsert_text_points(client, points, collection=collection)


def upsert_chunk_records(
    client: QdrantClient,
    records: list[ChunkRecord],
    collection: str | None = None,
    *,
    llm: Any | None = None,
) -> int:
    """Convenience wrapper for ChunkRecord lists."""
    points_data = [
        {
            "chunk_uid": r.chunk_uid,
            "text": r.chunk_text,
            "payload": {
                "document_code": r.document_code,
                "chunk_index": r.chunk_index,
                **r.metadata,
            },
        }
        for r in records
    ]
    return upsert_text_chunks(client, points_data, collection=collection, llm=llm)
