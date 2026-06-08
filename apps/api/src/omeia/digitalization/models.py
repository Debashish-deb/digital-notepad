"""Pydantic/dataclass models for the digitalization pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SourceFileManifest:
    """A discovered file before any extraction."""
    provider: str
    logical_path: str
    file_name: str
    file_ext: str
    size_bytes: int = 0
    modified_at: str | None = None
    checksum_sha256: str | None = None
    source_uri: str | None = None
    status: str = "discovered"
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str | None = None  # UUID from DB


@dataclass
class ExtractedDocument:
    """Raw extracted content from a single file."""
    manifest_id: str
    raw_text: str = ""
    raw_tables: list[dict[str, Any]] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    extractor_name: str = "unknown"
    extraction_status: str = "not_attempted"
    extraction_confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)
    id: str | None = None


@dataclass
class CanonicalSection:
    """A section within a canonical document."""
    heading: str = ""
    text: str = ""
    page_number: int | None = None
    sheet_name: str | None = None


@dataclass
class CanonicalDocument:
    """Normalized, validated, structured document."""
    manifest_id: str
    extracted_document_id: str
    document_id: str
    title: str = ""
    document_type: str = "unknown"
    domain: str = "unknown"
    language_original: str = "unknown"
    language_canonical: str = "en"
    canonical_json: dict[str, Any] = field(default_factory=dict)
    canonical_text: str = ""
    short_summary: str = ""
    should_index: bool = True
    needs_review: bool = False
    validation_status: str = "not_validated"
    warnings: list[str] = field(default_factory=list)
    id: str | None = None


@dataclass
class DocumentChunk:
    """A RAG-ready chunk derived from a canonical document."""
    canonical_document_id: str
    chunk_id: str
    chunk_index: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    token_count: int | None = None
    embedding_status: str = "not_started"
    id: str | None = None


@dataclass
class DigitalizationWarning:
    """A warning raised during any pipeline stage."""
    stage: str
    message: str
    severity: str = "warning"  # warning | error | info
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DigitalizationJob:
    """Tracks a single pipeline run."""
    provider: str = "local"
    root_path: str = ""
    status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    dry_run: bool = False
    error_summary: dict[str, Any] = field(default_factory=dict)
    created_by: str | None = None
    id: str | None = None

    # Derived counts populated after run
    counts: dict[str, int] = field(default_factory=dict)
