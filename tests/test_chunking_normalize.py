"""Phase 2 — chunking facade and normalize_chunks_for_indexer."""
from __future__ import annotations

from app_skeleton.api.chunking import (
    chunk_text,
    estimate_token_count,
    normalize_chunks_for_indexer,
)
from app_skeleton.api.platform_flags import canonical_chunk_pipeline_enabled


def test_chunk_text_returns_indexer_compatible_dicts() -> None:
    text = "Alpha paragraph one.\n\nBeta paragraph two with more words."
    chunks = chunk_text(text, section_path="docs/readme.md")
    assert chunks
    first = chunks[0]
    assert first["chunk_uid"] == "docs/readme.md::chunk_0000"
    assert first["chunk_text"] == first["text"]
    assert first["token_count"] == estimate_token_count(first["text"])
    assert first["chunk_index"] == 0


def test_normalize_chunks_for_indexer_maps_extraction_shape() -> None:
    raw = [
        {
            "chunk_index": 2,
            "chunk_id": "file::chunk_0002",
            "text": "Normalized body text for indexing.",
            "source_file": "policies/handbook.md",
            "word_count": 6,
        }
    ]
    out = normalize_chunks_for_indexer(raw, document_code="lab::overview::abc::handbook")
    assert len(out) == 1
    row = out[0]
    assert row["chunk_uid"] == "file::chunk_0002"
    assert row["chunk_text"] == "Normalized body text for indexing."
    assert row["metadata"]["source_file"] == "policies/handbook.md"
    assert row["metadata"]["word_count"] == 6


def test_normalize_skips_tiny_chunks() -> None:
    out = normalize_chunks_for_indexer(
        [{"text": "short"}],
        document_code="doc",
    )
    assert out == []


def test_canonical_chunk_pipeline_flag_defaults_false(monkeypatch) -> None:
    monkeypatch.delenv("CANONICAL_CHUNK_PIPELINE", raising=False)
    assert canonical_chunk_pipeline_enabled() is False
