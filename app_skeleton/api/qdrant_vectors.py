"""Portable Qdrant vector helpers — named vector ``text`` for doc_chunks everywhere."""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

LOGGER = logging.getLogger(__name__)

DOC_CHUNKS_COLLECTION = os.getenv("DOCUMENT_QDRANT_COLLECTION", "doc_chunks")
TEXT_VECTOR_NAME = os.getenv("DOCUMENT_QDRANT_VECTOR_NAME", "text")
EMBEDDING_DIM = int(os.getenv("TEXT_EMBEDDING_DIM", "384"))


def qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "http://localhost:6333").strip()


def qdrant_api_key() -> str | None:
    key = os.getenv("QDRANT_API_KEY", "").strip()
    return key or None


def get_qdrant_client(url: str | None = None) -> QdrantClient:
    return QdrantClient(url=url or qdrant_url(), api_key=qdrant_api_key())


def ping_qdrant(client: QdrantClient | None = None) -> bool:
    try:
        c = client or get_qdrant_client()
        c.get_collections()
        return True
    except Exception as exc:
        LOGGER.debug("Qdrant ping failed: %s", exc)
        return False


def ensure_named_text_collection(
    client: QdrantClient,
    collection: str | None = None,
) -> None:
    """Create collection with named vector ``text`` if missing (portable default)."""
    collection = collection or DOC_CHUNKS_COLLECTION
    try:
        client.get_collection(collection)
        return
    except Exception:
        pass
    client.create_collection(
        collection_name=collection,
        vectors_config={
            TEXT_VECTOR_NAME: models.VectorParams(
                size=EMBEDDING_DIM,
                distance=models.Distance.COSINE,
            ),
        },
    )
    LOGGER.info("Created Qdrant collection %s (vector=%s)", collection, TEXT_VECTOR_NAME)


def ensure_doc_chunks_collection(client: QdrantClient) -> None:
    ensure_named_text_collection(client, DOC_CHUNKS_COLLECTION)


def stable_point_uuid(seed: str) -> str:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return str(uuid.UUID(hex=digest))


def upsert_text_points(
    client: QdrantClient,
    points: list[models.PointStruct],
    *,
    collection: str | None = None,
) -> int:
    """Upsert points using named vector ``text``. Returns count upserted."""
    if not points:
        return 0
    collection = collection or DOC_CHUNKS_COLLECTION
    ensure_named_text_collection(client, collection)
    normalized: list[models.PointStruct] = []
    for pt in points:
        vec = pt.vector
        if isinstance(vec, list):
            vec = {TEXT_VECTOR_NAME: vec}
        elif isinstance(vec, dict) and TEXT_VECTOR_NAME not in vec and len(vec) == 1:
            vec = {TEXT_VECTOR_NAME: next(iter(vec.values()))}
        normalized.append(
            models.PointStruct(id=pt.id, vector=vec, payload=pt.payload or {})
        )
    client.upsert(collection_name=collection, points=normalized)
    return len(normalized)
