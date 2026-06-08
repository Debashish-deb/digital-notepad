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


def vectorization_enabled() -> bool:
    """When true, vault chunks are embedded into Qdrant and semantic vault search is enabled."""
    return _env_bool("VECTORIZATION_ENABLED", "false")


def vault_use_vector_indexer_enabled() -> bool:
    """When true, vault ingestion upserts via vector_indexer (shared embed path)."""
    return _env_bool("VAULT_USE_VECTOR_INDEXER", "false")


def canonical_chunk_pipeline_enabled() -> bool:
    """When true, all API chunking uses digitalization/chunker via chunking.py (no legacy char splits)."""
    return _env_bool("CANONICAL_CHUNK_PIPELINE", "false")


def ocr_enabled() -> bool:
    """When false (default), needs_ocr files stay metadata-only and the OCR worker idles."""
    return _env_bool("ENABLE_OCR", "false")


def project_rbac_enabled() -> bool:
    """When true, enforce project-level access via platform.project_member + researcher binding."""
    return _env_bool("PROJECT_RBAC_ENABLED", "false")


def research_strategy_assistant_enabled() -> bool:
    """When true, route strategic research questions through ResearchStrategyEngine."""
    return _env_bool("OMEIA_RESEARCH_STRATEGY_ASSISTANT", "false")


def strategy_report_mode_enabled() -> bool:
    """When true, include rendered markdown alongside structured strategy_report JSON."""
    return _env_bool("OMEIA_STRATEGY_REPORT_MODE", "true")


def strategy_external_search_enabled() -> bool:
    """When true, supplement strategy retrieval with research_knowledge_store external search."""
    return _env_bool("OMEIA_STRATEGY_EXTERNAL_SEARCH", "false")


def strategy_require_citations_enabled() -> bool:
    """When true, strategy answers require grounded references from retrieved evidence only."""
    return _env_bool("OMEIA_STRATEGY_REQUIRE_CITATIONS", "true")


def continuous_eval_enabled() -> bool:
    """When true, allow scheduled/triggered continuous quality eval runs."""
    return _env_bool("OMEIA_CONTINUOUS_EVAL_ENABLED", "false")


def quality_gate_strict_enabled() -> bool:
    """When true, quality eval failures/regressions mark run status as fail."""
    return _env_bool("OMEIA_QUALITY_GATE_STRICT", "false")


def continuous_learning_enabled() -> bool:
    """When true, record AI responses, run learning pipeline, and expose feedback API."""
    return _env_bool("OMEIA_CONTINUOUS_LEARNING_ENABLED", "false")


def expert_routing_enabled() -> bool:
    """When true, route specialist intents/categories to Layer 3 Ollama expert models."""
    return _env_bool("OMEIA_EXPERT_ROUTING_ENABLED", "false")


def learning_retrieval_boost_enabled() -> bool:
    """When true, verified lab knowledge items boost copilot retrieval ranking."""
    return _env_bool("OMEIA_LEARNING_RETRIEVAL_BOOST", "false")


def project_intelligence_briefs_enabled() -> bool:
    """When true, expose Project Intelligence Brief generation API."""
    return _env_bool("OMEIA_PROJECT_INTELLIGENCE_BRIEFS", "false")


def external_cancer_evidence_enabled() -> bool:
    """When true, merge external cancer evidence connectors into retrieval."""
    return _env_bool("OMEIA_EXTERNAL_CANCER_EVIDENCE", "false")


def lab_knowledge_threads_enabled() -> bool:
    """When true, expose Lab Knowledge Threads challenge/correct API."""
    return _env_bool("OMEIA_LAB_KNOWLEDGE_THREADS", "false")
