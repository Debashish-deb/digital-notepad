"""Single source for Qdrant collection names and vector dimensions."""
from __future__ import annotations

import os

from app_skeleton.api.embedding_service import embedding_dim

DOC_CHUNKS = os.getenv("DOCUMENT_QDRANT_COLLECTION", "doc_chunks")
RESEARCH_KB = os.getenv("RESEARCH_KB_QDRANT_COLLECTION", "research_knowledge")
VAULT_CHUNKS = os.getenv("VAULT_QDRANT_COLLECTION", "vault_asset_chunks")


def collection_dim() -> int:
    """Embedding dimension for all text vector collections."""
    raw = (os.getenv("TEXT_EMBEDDING_DIM") or os.getenv("RESEARCH_KB_VECTOR_SIZE") or "").strip()
    if raw:
        return int(raw)
    return embedding_dim()
