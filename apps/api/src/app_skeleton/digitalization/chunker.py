"""Chunker — create RAG-ready chunks from canonical documents."""
from __future__ import annotations

import hashlib
from typing import Any

from app_skeleton.digitalization.models import CanonicalDocument, DocumentChunk, SourceFileManifest
from app_skeleton.digitalization.secret_detector import scan_for_secrets

DEFAULT_CHUNK_SIZE_TOKENS = 700
DEFAULT_OVERLAP_TOKENS = 100
APPROX_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // APPROX_CHARS_PER_TOKEN)


def _split_text_into_chunks(
    text: str,
    chunk_size_tokens: int = DEFAULT_CHUNK_SIZE_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[str]:
    """Split text into overlapping chunks by approximate token count."""
    chunk_chars = chunk_size_tokens * APPROX_CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * APPROX_CHARS_PER_TOKEN

    if len(text) <= chunk_chars:
        return [text] if text.strip() else []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_chars
        # Try to break at a paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind("\n\n", start + chunk_chars // 2, end + 200)
            if para_break > start:
                end = para_break
            else:
                # Look for sentence break
                sent_break = text.rfind(". ", start + chunk_chars // 2, end + 100)
                if sent_break > start:
                    end = sent_break + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap_chars
        if start >= len(text):
            break

    return chunks


def chunk_document(
    manifest: SourceFileManifest,
    canonical: CanonicalDocument,
    *,
    chunk_size_tokens: int = DEFAULT_CHUNK_SIZE_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[DocumentChunk]:
    """Create chunks from a canonical document. Skips if should_index=false."""
    if not canonical.should_index:
        return []

    text = canonical.canonical_text or ""
    if not text.strip():
        return []

    # Double-check no secrets leak into chunks
    secret_scan = scan_for_secrets(text)
    if secret_scan.has_secrets:
        text = secret_scan.redacted_text

    # Try section-based chunking first
    sections = canonical.canonical_json.get("content", {}).get("sections", [])
    chunks: list[DocumentChunk] = []
    chunk_idx = 0

    canonical_doc_id = canonical.id or canonical.document_id or ""

    base_metadata: dict[str, Any] = {
        "document_id": canonical.document_id,
        "source_file": manifest.file_name,
        "provider": manifest.provider,
        "logical_path": manifest.logical_path,
        "domain": canonical.domain,
        "document_type": canonical.document_type,
        "language": canonical.language_canonical,
    }

    if sections and len(sections) > 1:
        # Section-then-token strategy
        for section in sections:
            section_text = section.get("text", "").strip()
            if not section_text:
                continue
            heading = section.get("heading", "")
            section_chunks = _split_text_into_chunks(section_text, chunk_size_tokens, overlap_tokens)
            for sub_text in section_chunks:
                chunk_id = _make_chunk_id(canonical.document_id, chunk_idx)
                meta = {
                    **base_metadata,
                    "section_heading": heading,
                    "page_number": section.get("page_number"),
                    "sheet_name": section.get("sheet_name"),
                }
                chunks.append(DocumentChunk(
                    canonical_document_id=canonical_doc_id,
                    chunk_id=chunk_id,
                    chunk_index=chunk_idx,
                    text=sub_text,
                    metadata=meta,
                    token_count=_estimate_tokens(sub_text),
                ))
                chunk_idx += 1
    else:
        # Flat chunking
        text_chunks = _split_text_into_chunks(text, chunk_size_tokens, overlap_tokens)
        for sub_text in text_chunks:
            chunk_id = _make_chunk_id(canonical.document_id, chunk_idx)
            chunks.append(DocumentChunk(
                canonical_document_id=canonical_doc_id,
                chunk_id=chunk_id,
                chunk_index=chunk_idx,
                text=sub_text,
                metadata=base_metadata,
                token_count=_estimate_tokens(sub_text),
            ))
            chunk_idx += 1

    return chunks


def _make_chunk_id(document_id: str, index: int) -> str:
    raw = f"{document_id}:chunk:{index}"
    return f"chunk_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"
