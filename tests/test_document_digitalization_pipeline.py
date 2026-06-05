"""Tests for the data digitalization pipeline."""
from __future__ import annotations

import tempfile
import pytest
from pathlib import Path
from app_skeleton.digitalization.models import SourceFileManifest, ExtractedDocument, CanonicalDocument
from app_skeleton.digitalization import validators, canonicalizer, chunker, status, secret_detector

def test_status_lifecycle():
    assert status.Status.is_digitalized("canonicalized")
    assert not status.Status.is_digitalized("discovered")
    assert not status.Status.is_digitalized("extracted")
    assert status.Status.is_terminal("extraction_failed")

def test_secret_detector():
    text = "Here is my secret api_key: 'AKIA1234567890123456' don't tell anyone."
    result = secret_detector.scan_for_secrets(text)
    assert result.has_secrets
    assert len(result.matches) == 1
    assert "AKIA" not in result.redacted_text
    assert "[REDACTED:" in result.redacted_text

def test_secret_detector_no_secrets():
    text = "This is a normal public document about CyCif."
    result = secret_detector.scan_for_secrets(text)
    assert not result.has_secrets
    assert result.redacted_text == text

def test_canonicalizer():
    manifest = SourceFileManifest(
        provider="local",
        logical_path="protocols/staining_protocol.md",
        file_name="staining_protocol.md",
        file_ext=".md",
        size_bytes=1000,
    )
    extracted = ExtractedDocument(
        manifest_id="dummy",
        raw_text="# Staining Protocol\n\nThis is a long text about how to stain CyCif tissues. " * 10,
        extraction_status="extracted",
        extraction_confidence=0.9,
    )

    canonical = canonicalizer.canonicalize(manifest, extracted)
    assert canonical.document_type == "protocol"
    assert canonical.domain == "research"
    assert canonical.title == "Staining Protocol"
    assert canonical.should_index is True
    assert canonical.needs_review is False

def test_validator_path_only_fake():
    doc = CanonicalDocument(
        manifest_id="dummy",
        extracted_document_id="dummy",
        document_id="dummy_doc",
        title="Fake",
        canonical_json={"schema_version": "1.0", "source": {"file_name": "a", "logical_path": "a"}},
        canonical_text="/data/group/OMEIA/some_folder/my_file.pdf\n",
    )
    v_status, warnings = validators.validate_canonical(doc)
    assert v_status == "validation_failed"
    assert any("path-only" in w for w in warnings)

def test_chunker():
    manifest = SourceFileManifest(
        provider="local",
        logical_path="test.txt",
        file_name="test.txt",
        file_ext=".txt",
    )
    doc = CanonicalDocument(
        manifest_id="dummy",
        extracted_document_id="dummy",
        document_id="dummy_doc",
        should_index=True,
        canonical_text="Word. " * 500,
        canonical_json={},
    )
    
    # Should create a few chunks based on chunk size
    chunks = chunker.chunk_document(manifest, doc, chunk_size_tokens=100, overlap_tokens=20)
    assert len(chunks) > 1
    assert chunks[0].canonical_document_id == "dummy_doc"
