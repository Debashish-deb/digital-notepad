"""Phase 1 qdrant_collections single source of truth."""
from __future__ import annotations

from omeia.api.qdrant_collections import (
    DOC_CHUNKS,
    RESEARCH_KB,
    VAULT_CHUNKS,
    all_collections,
    readiness_collections,
    resolve_collection,
)


def test_all_collections_keys() -> None:
    cols = all_collections()
    assert cols["doc_chunks"] == DOC_CHUNKS
    assert cols["research_knowledge"] == RESEARCH_KB
    assert cols["vault_asset_chunks"] == VAULT_CHUNKS


def test_resolve_collection_by_kind() -> None:
    assert resolve_collection("vault") == VAULT_CHUNKS
    assert resolve_collection("research") == RESEARCH_KB
    assert resolve_collection("doc") == DOC_CHUNKS


def test_resolve_collection_explicit_override() -> None:
    assert resolve_collection("doc", explicit="custom_coll") == "custom_coll"


def test_readiness_collections_default_excludes_vault(monkeypatch) -> None:
    monkeypatch.delenv("VECTORIZATION_ENABLED", raising=False)
    monkeypatch.setenv("VECTORIZATION_ENABLED", "false")
    cols = readiness_collections()
    assert set(cols) == {"doc_chunks", "research_knowledge"}
