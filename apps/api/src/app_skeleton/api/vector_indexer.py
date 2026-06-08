"""Single upsert entry for doc_chunks, research_knowledge, vault_asset_chunks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app_skeleton.api.embedding_service import embed_text
from app_skeleton.api.qdrant_collections import (
    DOC_CHUNKS,
    RESEARCH_KB,
    VAULT_CHUNKS,
    CollectionKind,
    collection_dim,
    resolve_collection,
)
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
    kind: CollectionKind | str | None = "doc",
    llm: Any | None = None,
) -> int:
    """Embed and upsert chunk dicts: each item needs chunk_uid, text, payload."""
    if not points_data:
        return 0
    collection = resolve_collection(kind, explicit=collection)
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
    kind: CollectionKind | str | None = "doc",
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
    return upsert_text_chunks(
        client,
        points_data,
        collection=collection,
        kind=kind,
        llm=llm,
    )


def upsert_vault_asset_chunks(
    client: QdrantClient,
    asset_id: str,
    chunks: list[dict[str, Any]],
    *,
    source_path: str = "",
    filename: str = "",
    logical_path: str = "",
    checksum_sha256: str = "",
    llm: Any | None = None,
) -> int:
    """Upsert vault extraction chunks into vault_asset_chunks via shared embed path."""
    points_data: list[dict[str, Any]] = []
    for chunk in chunks[:50]:
        text = (chunk.get("text") or "").strip()
        if len(text) < 8:
            continue
        chunk_key = chunk.get("chunk_id") or chunk.get("chunk_index") or len(points_data)
        chunk_uid = f"{asset_id}:{chunk_key}"
        chunk_meta = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        points_data.append({
            "chunk_uid": chunk_uid,
            "text": text,
            "payload": {
                "asset_id": asset_id,
                "source_file": source_path,
                "filename": filename or chunk_meta.get("filename") or "",
                "logical_path": logical_path or chunk_meta.get("logical_path") or source_path,
                "checksum_sha256": checksum_sha256 or chunk_meta.get("checksum_sha256") or "",
                "chunk_index": chunk.get("chunk_index"),
                "text_preview": text[:2000],
            },
        })
    return upsert_text_chunks(
        client,
        points_data,
        collection=VAULT_CHUNKS,
        kind="vault",
        llm=llm,
    )


def upsert_research_kb_chunks(
    client: QdrantClient,
    points_data: list[dict[str, Any]],
    *,
    llm: Any | None = None,
) -> int:
    """Upsert research knowledge chunks into research_knowledge collection."""
    return upsert_text_chunks(
        client,
        points_data,
        collection=RESEARCH_KB,
        kind="research",
        llm=llm,
    )
