"""Feature flags for incremental platform remediation (Phase 1+)."""
from __future__ import annotations

import os


def _env_bool(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in ("1", "true", "yes", "on")


def knowledge_indexer_enabled() -> bool:
    return _env_bool("KNOWLEDGE_INDEXER_ENABLED", "false")


def platform_chunk_write_enabled() -> bool:
    """When false, skip new inserts into platform.document_chunk (legacy table)."""
    return _env_bool("PLATFORM_CHUNK_WRITE", "true")


def vault_json_fallback_enabled() -> bool:
    """When false, vault search uses Postgres only (no JSON inventory fallback)."""
    return _env_bool("VAULT_JSON_FALLBACK", "true")


def require_auth_static_enabled() -> bool:
    """When true, /database-static and /projects-static require Bearer auth."""
    return _env_bool("REQUIRE_AUTH_STATIC", "false")


def vault_use_vector_indexer_enabled() -> bool:
    """When true, vault ingestion upserts via vector_indexer (shared embed path)."""
    return _env_bool("VAULT_USE_VECTOR_INDEXER", "false")


def canonical_chunk_pipeline_enabled() -> bool:
    """When true, all API chunking uses digitalization/chunker via chunking.py (no legacy char splits)."""
    return _env_bool("CANONICAL_CHUNK_PIPELINE", "false")


def ocr_enabled() -> bool:
    """When false (default), needs_ocr files stay metadata-only and the OCR worker idles."""
    return _env_bool("ENABLE_OCR", "false")
