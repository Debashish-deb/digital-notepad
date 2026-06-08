"""Tests for vector_indexer shared upsert path."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app_skeleton.api.vector_indexer import ChunkRecord, build_point_from_chunk, upsert_text_chunks


def test_build_point_from_chunk_uses_embed_text():
    with patch("app_skeleton.api.vector_indexer.embed_text", return_value=[0.1, 0.2, 0.3]) as mock_embed:
        pt = build_point_from_chunk(
            "doc::chunk_0001",
            "Sample chunk text for embedding",
            {"document_code": "DOC-1"},
            dim=3,
        )
        mock_embed.assert_called_once()
        assert pt.payload["document_code"] == "DOC-1"
        assert pt.payload["chunk_uid"] == "doc::chunk_0001"
        assert "text" in pt.vector


def test_upsert_text_chunks_skips_short_text():
    client = MagicMock()
    with patch("app_skeleton.api.vector_indexer.upsert_text_points", return_value=0) as mock_upsert:
        n = upsert_text_chunks(client, [{"chunk_uid": "x", "text": "short", "payload": {}}], collection="doc_chunks")
        assert n == 0
        mock_upsert.assert_not_called()


def test_upsert_text_chunks_batches_to_qdrant():
    client = MagicMock()
    points_data = [
        {"chunk_uid": "uid-1", "text": "Enough text here for embedding.", "payload": {"k": 1}},
    ]
    with patch("app_skeleton.api.vector_indexer.embed_text", return_value=[0.5] * 384):
        with patch("app_skeleton.api.vector_indexer.upsert_text_points", return_value=1) as mock_upsert:
            n = upsert_text_chunks(client, points_data, collection="doc_chunks")
            assert n == 1
            mock_upsert.assert_called_once()


def test_chunk_record_dataclass():
    rec = ChunkRecord(
        chunk_uid="DOC-CHK-0",
        chunk_text="hello world chunk",
        document_code="DOC",
        chunk_index=0,
        metadata={"corpus": "lab_operations"},
    )
    assert rec.chunk_index == 0
    assert rec.metadata["corpus"] == "lab_operations"
