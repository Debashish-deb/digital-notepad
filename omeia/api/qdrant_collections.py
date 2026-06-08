"""Single source for Qdrant collection names and vector dimensions."""
from __future__ import annotations

import os
from typing import Literal

from omeia.api.embedding_service import embedding_dim

DOC_CHUNKS = os.getenv("DOCUMENT_QDRANT_COLLECTION", "doc_chunks")
RESEARCH_KB = os.getenv("RESEARCH_KB_QDRANT_COLLECTION", "research_knowledge")
VAULT_CHUNKS = os.getenv("VAULT_QDRANT_COLLECTION", "vault_asset_chunks")

CollectionKind = Literal["doc", "research", "vault"]

_COLLECTION_BY_KIND: dict[str, str] = {
    "doc": DOC_CHUNKS,
    "research": RESEARCH_KB,
    "vault": VAULT_CHUNKS,
}


def collection_dim() -> int:
    """Embedding dimension for all text vector collections."""
    raw = (os.getenv("TEXT_EMBEDDING_DIM") or os.getenv("RESEARCH_KB_VECTOR_SIZE") or "").strip()
    if raw:
        return int(raw)
    return embedding_dim()


def resolve_collection(
    kind: CollectionKind | str | None = None,
    *,
    explicit: str | None = None,
) -> str:
    """Resolve collection name from kind or explicit override."""
    if explicit and explicit.strip():
        return explicit.strip()
    if kind and kind in _COLLECTION_BY_KIND:
        return _COLLECTION_BY_KIND[kind]
    return DOC_CHUNKS


def all_collections() -> dict[str, str]:
    """Logical name → Qdrant collection name (for admin health / migrations)."""
    return {
        "doc_chunks": DOC_CHUNKS,
        "research_knowledge": RESEARCH_KB,
        "vault_asset_chunks": VAULT_CHUNKS,
    }


def readiness_collections() -> dict[str, str]:
    """Collections required for /ready when Qdrant indexing checks are active."""
    from omeia.api.platform_flags import vectorization_enabled

    cols = {
        "doc_chunks": DOC_CHUNKS,
        "research_knowledge": RESEARCH_KB,
    }
    if vectorization_enabled():
        cols["vault_asset_chunks"] = VAULT_CHUNKS
    return cols


def collection_kinds() -> tuple[str, ...]:
    return tuple(_COLLECTION_BY_KIND.keys())
