from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

from qdrant_client import QdrantClient, models

from omeia.api.embedding_service import embed_text, embedding_dim
from omeia.api.qdrant_collections import RESEARCH_KB as COLLECTION
from omeia.api.qdrant_vectors import ensure_named_text_collection, upsert_text_points

LOGGER = logging.getLogger(__name__)

VECTOR_NAME = os.getenv("RESEARCH_KB_QDRANT_VECTOR_NAME", "text")


def vector_size() -> int:
    raw = (os.getenv("RESEARCH_KB_VECTOR_SIZE") or "").strip()
    return int(raw or embedding_dim())


def __getattr__(name: str) -> int | str:
    if name == "VECTOR_SIZE":
        return vector_size()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def stable_point_id(*parts: str) -> str:
    raw = "::".join(str(p or "") for p in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:32]


def ensure_research_collection(qdrant: QdrantClient) -> dict[str, Any]:
    existed = False
    try:
        qdrant.get_collection(COLLECTION)
        existed = True
    except Exception:
        pass
    ensure_named_text_collection(qdrant, COLLECTION)
    info = qdrant.get_collection(COLLECTION)
    config = info.config.params.vectors
    schema_ok = isinstance(config, dict) and VECTOR_NAME in config
    return {"created": not existed, "schema_ok": schema_ok, "collection": COLLECTION, "vector_name": VECTOR_NAME}


def _embed_chunk(text: str, embedder: Any | None) -> list[float]:
    dim = vector_size()
    if embedder is not None and hasattr(embedder, "embed"):
        return embedder.embed(text, dim=dim)
    return embed_text(text, dim=dim, llm=embedder)


def upsert_research_chunks(
    qdrant: QdrantClient,
    embedder: Any,
    chunks: list[dict[str, Any]],
    base_payload: dict[str, Any],
) -> dict[str, Any]:
    status = ensure_research_collection(qdrant)
    if not status.get("schema_ok"):
        raise RuntimeError(
            f"Qdrant collection {COLLECTION} exists but does not have named vector {VECTOR_NAME!r}. Reindex required."
        )

    points = []
    for chunk in chunks:
        text = chunk["text"]
        vector = _embed_chunk(text, embedder)
        point_id = stable_point_id(base_payload.get("document_id"), str(chunk["chunk_index"]), chunk.get("text_hash"))
        payload = {
            **base_payload,
            "chunk_index": chunk["chunk_index"],
            "chunk_id": chunk.get("chunk_id") or point_id,
            "section_title": chunk.get("section_title"),
            "text": text,
            "text_hash": chunk.get("text_hash"),
            "token_count": chunk.get("token_count"),
        }
        points.append(models.PointStruct(id=point_id, vector={VECTOR_NAME: vector}, payload=payload))

    if points:
        upsert_text_points(qdrant, points, collection=COLLECTION)
    return {"collection": COLLECTION, "vector_name": VECTOR_NAME, "points_indexed": len(points)}


def search_research_knowledge(
    qdrant: QdrantClient,
    embedder: Any,
    query: str,
    limit: int = 20,
    access_levels: list[str] | None = None,
) -> list[dict[str, Any]]:
    ensure_research_collection(qdrant)
    vector = _embed_chunk(query, embedder)
    must = []
    if access_levels:
        must.append(models.FieldCondition(key="visibility", match=models.MatchAny(any=access_levels)))
    qfilter = models.Filter(must=must) if must else None
    result = qdrant.query_points(
        collection_name=COLLECTION,
        query=vector,
        using=VECTOR_NAME,
        query_filter=qfilter,
        limit=max(1, min(limit, 100)),
    )
    hits = []
    for point in getattr(result, "points", []) or []:
        payload = point.payload or {}
        hits.append({
            "id": str(point.id),
            "score": float(point.score or 0.0),
            "title": payload.get("title") or "Untitled",
            "snippet": str(payload.get("text") or "")[:900],
            "source_url": payload.get("source_url"),
            "source_type": payload.get("source_type"),
            "doi": payload.get("doi"),
            "pmid": payload.get("pmid"),
            "dataset_accession": payload.get("dataset_accession"),
            "entities": payload.get("entities") or [],
            "metadata": payload,
        })
    return hits
