"""Thin facade to digitalization/chunker — single chunk authority for API callers."""
from __future__ import annotations

import os
import re
from typing import Any

from app_skeleton.digitalization.chunker import (
    APPROX_CHARS_PER_TOKEN,
    DEFAULT_CHUNK_SIZE_TOKENS,
    DEFAULT_OVERLAP_TOKENS,
    _estimate_tokens,
    _split_text_into_chunks,
)


def _chunk_size_tokens() -> int:
    raw = (os.getenv("CHUNK_SIZE_TOKENS") or "").strip()
    return int(raw) if raw else DEFAULT_CHUNK_SIZE_TOKENS


def _overlap_tokens() -> int:
    raw = (os.getenv("CHUNK_OVERLAP_TOKENS") or "").strip()
    return int(raw) if raw else DEFAULT_OVERLAP_TOKENS


def _count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9\u00C0-\uFFFF]+", text or ""))


def estimate_token_count(text: str) -> int:
    """Approximate token count aligned with digitalization/chunker."""
    return _estimate_tokens(text or "")


def chunk_text(text: str, *, section_path: str = "") -> list[dict[str, Any]]:
    """Token-based chunking via digitalization/chunker; returns extraction-compatible dicts."""
    text = (text or "").strip()
    if not text:
        return []
    parts = _split_text_into_chunks(
        text,
        chunk_size_tokens=_chunk_size_tokens(),
        overlap_tokens=_overlap_tokens(),
    )
    chunks: list[dict[str, Any]] = []
    offset = 0
    for idx, part in enumerate(parts):
        start = text.find(part, offset)
        if start < 0:
            start = offset
        end = start + len(part)
        offset = max(end - _overlap_tokens() * APPROX_CHARS_PER_TOKEN, start + 1)
        chunk_id = f"{section_path}::chunk_{idx:04d}" if section_path else f"chunk_{idx:04d}"
        chunks.append({
            "chunk_id": chunk_id,
            "chunk_uid": chunk_id,
            "source_file": section_path,
            "chunk_index": idx,
            "start_char": start,
            "end_char": end,
            "char_count": len(part),
            "word_count": _count_words(part),
            "text": part,
            "chunk_text": part,
            "token_count": estimate_token_count(part),
        })
    return chunks


def normalize_chunks_for_indexer(
    chunks: list[dict[str, Any]],
    *,
    document_code: str,
) -> list[dict[str, Any]]:
    """Map extraction/digitalization chunk dicts to knowledge_indexer write shape."""
    normalized: list[dict[str, Any]] = []
    for raw in chunks:
        text = (raw.get("chunk_text") or raw.get("text") or "").strip()
        if len(text) < 8:
            continue
        idx = int(raw.get("chunk_index") or len(normalized))
        chunk_uid = (
            raw.get("chunk_uid")
            or raw.get("chunk_id")
            or f"{document_code}::chunk_{idx:04d}"
        )
        metadata = dict(raw.get("metadata") or {})
        for key in (
            "source_file",
            "section_title",
            "section_heading",
            "start_char",
            "end_char",
            "char_count",
            "word_count",
            "text_hash",
        ):
            if key in raw and key not in metadata:
                metadata[key] = raw[key]
        normalized.append({
            "chunk_index": idx,
            "chunk_uid": chunk_uid,
            "chunk_text": text,
            "text": text,
            "token_count": raw.get("token_count") or estimate_token_count(text),
            "metadata": metadata,
        })
    return normalized
