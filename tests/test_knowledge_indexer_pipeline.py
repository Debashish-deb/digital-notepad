"""Phase 2 — knowledge_indexer canonical pipeline (unit, no DB)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app_skeleton.api.knowledge_indexer import (
    index_document_text,
    index_extraction_chunks,
    index_section_twin,
    index_vault_extraction,
    write_chunks,
)


def test_write_chunks_disabled_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KNOWLEDGE_INDEXER_ENABLED", "false")
    result = write_chunks(
        document_code="proj::doc",
        title="Doc",
        source_type="md",
        metadata={},
        chunks=[{"chunk_index": 0, "text": "hello world chunk"}],
    )
    assert result["enabled"] is False
    assert result["chunks_written"] == 0


@patch("app_skeleton.api.knowledge_indexer.write_chunks")
def test_index_extraction_chunks_delegates(mock_write: MagicMock) -> None:
    mock_write.return_value = {"enabled": True, "chunks_written": 1}
    out = index_extraction_chunks(
        document_code="X",
        title="T",
        source_type="txt",
        chunks=[{"text": "sample chunk text"}],
        metadata={"k": "v"},
    )
    mock_write.assert_called_once()
    assert out["chunks_written"] == 1


@patch("app_skeleton.api.knowledge_indexer.index_extraction_chunks")
@patch("app_skeleton.api.knowledge_indexer.chunk_text")
def test_index_document_text_chunks_then_indexes(
    mock_chunk: MagicMock,
    mock_index: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KNOWLEDGE_INDEXER_ENABLED", "true")
    mock_chunk.return_value = [{"chunk_index": 0, "text": "chunk one", "chunk_uid": "c0"}]
    mock_index.return_value = {"chunks_written": 1}
    index_document_text(
        document_code="doc-1",
        title="Title",
        source_type="md",
        text="Long body text for chunking.",
        metadata={"corpus": "test"},
        section_path="notes.md",
    )
    mock_chunk.assert_called_once()
    mock_index.assert_called_once()


def test_index_vault_extraction_uses_stable_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KNOWLEDGE_INDEXER_ENABLED", "false")
    with patch("app_skeleton.api.knowledge_indexer.index_extraction_chunks") as mock_index:
        index_vault_extraction(
            asset_id="asset-42",
            filename="paper.pdf",
            chunks=[{"text": "vault chunk content"}],
            metadata={"logical_path": "vault/paper.pdf"},
        )
        mock_index.assert_called_once()
        kwargs = mock_index.call_args.kwargs
        assert kwargs["document_code"] == "vault:asset-42"
        assert kwargs["source_type"] == "vault_asset"


def test_index_section_twin_disabled_short_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KNOWLEDGE_INDEXER_ENABLED", "false")
    twin = {
        "document_index": [{"path": "a.md", "title": "A", "excerpt": "hello"}],
        "vector_chunks": [],
    }
    out = index_section_twin(section_id="overview", section_label="Overview", twin=twin)
    assert out["enabled"] is False
    assert out["documents_indexed"] == 0
