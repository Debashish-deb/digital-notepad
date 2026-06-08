"""Readiness probes: required Qdrant collections depend on feature flags."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from omeia.api.qdrant_collections import readiness_collections
from omeia.api.readiness import _qdrant_ready


def _mock_collection_info(size: int = 768) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(
                vectors=SimpleNamespace(vectors=SimpleNamespace(size=size)),
            ),
        ),
    )


def test_readiness_collections_excludes_vault_without_vectorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KNOWLEDGE_INDEXER_ENABLED", "true")
    monkeypatch.setenv("VECTORIZATION_ENABLED", "false")
    cols = readiness_collections()
    assert "doc_chunks" in cols
    assert "research_knowledge" in cols
    assert "vault_asset_chunks" not in cols


def test_readiness_collections_includes_vault_with_vectorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KNOWLEDGE_INDEXER_ENABLED", "true")
    monkeypatch.setenv("VECTORIZATION_ENABLED", "true")
    cols = readiness_collections()
    assert cols["vault_asset_chunks"] == "vault_asset_chunks"


def test_qdrant_ready_ignores_missing_vault_when_vectorization_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KNOWLEDGE_INDEXER_ENABLED", "true")
    monkeypatch.setenv("VECTORIZATION_ENABLED", "false")
    monkeypatch.setenv("TEXT_EMBEDDING_DIM", "768")

    client = MagicMock()

    def get_collection(name: str) -> MagicMock:
        if name == "vault_asset_chunks":
            raise RuntimeError("404 Not Found")
        return _mock_collection_info(768)

    client.get_collection.side_effect = get_collection

    ok, err = _qdrant_ready(client)
    assert ok is True
    assert err is None


def test_qdrant_ready_fails_when_vault_missing_and_vectorization_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KNOWLEDGE_INDEXER_ENABLED", "true")
    monkeypatch.setenv("VECTORIZATION_ENABLED", "true")
    monkeypatch.setenv("TEXT_EMBEDDING_DIM", "768")

    client = MagicMock()

    def get_collection(name: str) -> MagicMock:
        if name == "vault_asset_chunks":
            raise RuntimeError("404 Not Found")
        return _mock_collection_info(768)

    client.get_collection.side_effect = get_collection

    ok, err = _qdrant_ready(client)
    assert ok is False
    assert err is not None
    assert "vault_asset_chunks" in err
