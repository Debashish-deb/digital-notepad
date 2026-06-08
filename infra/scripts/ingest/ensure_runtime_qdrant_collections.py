#!/usr/bin/env python3
"""Ensure runtime Qdrant text collections exist (doc, research, vault when enabled).

Usage:
  PYTHONPATH=. python scripts/ingest/ensure_runtime_qdrant_collections.py

Honors KNOWLEDGE_INDEXER_ENABLED / VECTORIZATION_ENABLED — vault collection is
created only when VECTORIZATION_ENABLED=true.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from omeia.api.platform_flags import vectorization_enabled
from omeia.api.qdrant_collections import DOC_CHUNKS, RESEARCH_KB, VAULT_CHUNKS, collection_dim
from omeia.api.qdrant_vectors import ensure_named_text_collection, get_qdrant_client

LOGGER = logging.getLogger(__name__)


def ensure_runtime_collections() -> list[str]:
    """Create missing runtime collections; return names ensured."""
    client = get_qdrant_client()
    ensured: list[str] = []
    for name in (DOC_CHUNKS, RESEARCH_KB):
        ensure_named_text_collection(client, name)
        ensured.append(name)
    if vectorization_enabled():
        ensure_named_text_collection(client, VAULT_CHUNKS)
        ensured.append(VAULT_CHUNKS)
    return ensured


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    dim = collection_dim()
    LOGGER.info("Ensuring runtime Qdrant collections (dim=%s, vault=%s)", dim, vectorization_enabled())
    try:
        names = ensure_runtime_collections()
    except Exception as exc:
        LOGGER.error("Failed to ensure Qdrant collections: %s", exc)
        return 1
    for name in names:
        LOGGER.info("OK: %s", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
