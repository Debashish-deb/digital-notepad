"""Postgres CRUD for Teacher-Student continuous learning tables."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from psycopg.types.json import Jsonb

from omeia.api.db_pool import get_db_connection
from omeia.api.learning_models import StorageStatus

LOGGER = logging.getLogger(__name__)

_SCHEMA_TABLE = "platform.ai_responses"


def schema_available() -> bool:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('platform.ai_responses');")
                return bool(cur.fetchone()[0])
    except Exception as exc:
        LOGGER.debug("Learning schema check failed: %s", exc)
        return False


def _row_to_dict(row: tuple, columns: list[str]) -> dict[str, Any]:
    return {col: val for col, val in zip(columns, row)}


def insert_ai_response(
    *,
    query_text: str,
    answer_text: str,
    user_email: str | None = None,
    session_id: str | None = None,
    model_provider: str | None = None,
    model_name: str | None = None,
    model_role: str = "student",
    intent: str | None = None,
    project_codes: list[str] | None = None,
    source_ids: list[dict[str, Any]] | None = None,
    citation_count: int = 0,
    has_citations: bool = False,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    if not schema_available():
        return None
    response_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.ai_responses (
                        response_id, session_id, user_email, query_text, answer_text,
                        model_provider, model_name, model_role, intent, project_codes,
                        source_ids, citation_count, has_citations, pipeline_status,
                        metadata, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        response_id,
                        session_id,
                        user_email,
                        query_text,
                        answer_text,
                        model_provider,
                        model_name,
                        model_role,
                        intent,
                        project_codes or [],
                        Jsonb(source_ids or []),
                        citation_count,
                        has_citations,
                        "pending",
                        Jsonb(metadata or {}),
                        now,
                        now,
                    ),
                )
            conn.commit()
        return response_id
    except Exception as exc:
        LOGGER.warning("insert_ai_response failed: %s", exc)
        return None


def update_pipeline_status(response_id: str, status: str) -> bool:
    if not schema_available():
        return False
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE platform.ai_responses
                    SET pipeline_status = %s, updated_at = %s
                    WHERE response_id = %s
                    """,
                    (status, datetime.now(timezone.utc), response_id),
                )
            conn.commit()
        return True
    except Exception as exc:
        LOGGER.warning("update_pipeline_status failed: %s", exc)
        return False


def insert_claim(
    *,
    response_id: str,
    claim_text: str,
    claim_type: str = "factual",
    confidence_score: float = 0.0,
    has_citation: bool = False,
    extraction_method: str = "rule_based",
    metadata: dict[str, Any] | None = None,
) -> str | None:
    claim_id = str(uuid.uuid4())
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.extracted_claims (
                        claim_id, response_id, claim_text, claim_type,
                        confidence_score, has_citation, extraction_method, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        claim_id,
                        response_id,
                        claim_text,
                        claim_type,
                        confidence_score,
                        has_citation,
                        extraction_method,
                        Jsonb(metadata or {}),
                    ),
                )
            conn.commit()
        return claim_id
    except Exception as exc:
        LOGGER.warning("insert_claim failed: %s", exc)
        return None


def insert_evidence(
    *,
    response_id: str,
    claim_id: str | None = None,
    source_type: str = "citation",
    title: str | None = None,
    url: str | None = None,
    doi: str | None = None,
    pmid: str | None = None,
    accession: str | None = None,
    chunk_id: str | None = None,
    source_uuid: str | None = None,
    excerpt: str | None = None,
    confidence_score: float = 0.0,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    evidence_id = str(uuid.uuid4())
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.evidence_sources (
                        evidence_id, response_id, claim_id, source_type, title, url,
                        doi, pmid, accession, chunk_id, source_uuid, excerpt,
                        confidence_score, metadata
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        evidence_id,
                        response_id,
                        claim_id,
                        source_type,
                        title,
                        url,
                        doi,
                        pmid,
                        accession,
                        chunk_id,
                        source_uuid,
                        excerpt,
                        confidence_score,
                        Jsonb(metadata or {}),
                    ),
                )
            conn.commit()
        return evidence_id
    except Exception as exc:
        LOGGER.warning("insert_evidence failed: %s", exc)
        return None


def insert_knowledge_item(
    *,
    response_id: str | None,
    claim_id: str | None,
    title: str,
    content: str,
    storage_status: str,
    confidence_score: float,
    has_citation: bool,
    entity_type: str | None = None,
    classification: str | None = None,
    supersedes_id: str | None = None,
    contradiction_flags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    knowledge_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.knowledge_items (
                        knowledge_id, response_id, claim_id, title, content,
                        storage_status, confidence_score, has_citation, entity_type,
                        classification, version, supersedes_id, contradiction_flags,
                        metadata, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s,%s)
                    """,
                    (
                        knowledge_id,
                        response_id,
                        claim_id,
                        title,
                        content,
                        storage_status,
                        confidence_score,
                        has_citation,
                        entity_type,
                        classification,
                        supersedes_id,
                        Jsonb(contradiction_flags or []),
                        Jsonb(metadata or {}),
                        now,
                        now,
                    ),
                )
            conn.commit()
        return knowledge_id
    except Exception as exc:
        LOGGER.warning("insert_knowledge_item failed: %s", exc)
        return None


def update_knowledge_status(
    knowledge_id: str,
    storage_status: str,
    *,
    confidence_score: float | None = None,
    deprecate: bool = False,
) -> bool:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if deprecate:
                    cur.execute(
                        """
                        UPDATE platform.knowledge_items
                        SET storage_status = %s,
                            deprecated_at = %s,
                            updated_at = %s,
                            confidence_score = COALESCE(%s, confidence_score)
                        WHERE knowledge_id = %s
                        """,
                        (
                            StorageStatus.DEPRECATED.value,
                            datetime.now(timezone.utc),
                            datetime.now(timezone.utc),
                            confidence_score,
                            knowledge_id,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE platform.knowledge_items
                        SET storage_status = %s,
                            updated_at = %s,
                            confidence_score = COALESCE(%s, confidence_score)
                        WHERE knowledge_id = %s
                        """,
                        (
                            storage_status,
                            datetime.now(timezone.utc),
                            confidence_score,
                            knowledge_id,
                        ),
                    )
            conn.commit()
        return True
    except Exception as exc:
        LOGGER.warning("update_knowledge_status failed: %s", exc)
        return False


def insert_graph_edge(
    *,
    knowledge_id: str | None,
    subject_name: str,
    subject_type: str,
    relation_type: str,
    object_name: str,
    object_type: str,
    confidence_score: float = 0.0,
    evidence_text: str | None = None,
    storage_status: str = StorageStatus.DRAFT.value,
    supersedes_edge_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    edge_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.knowledge_graph_edges (
                        edge_id, knowledge_id, subject_name, subject_type, relation_type,
                        object_name, object_type, confidence_score, evidence_text,
                        storage_status, version, supersedes_edge_id, metadata,
                        created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s)
                    """,
                    (
                        edge_id,
                        knowledge_id,
                        subject_name,
                        subject_type,
                        relation_type,
                        object_name,
                        object_type,
                        confidence_score,
                        evidence_text,
                        storage_status,
                        supersedes_edge_id,
                        Jsonb(metadata or {}),
                        now,
                        now,
                    ),
                )
            conn.commit()
        return edge_id
    except Exception as exc:
        LOGGER.warning("insert_graph_edge failed: %s", exc)
        return None


def insert_feedback(
    *,
    response_id: str,
    user_email: str,
    feedback_type: str,
    rating: int | None = None,
    comment: str | None = None,
    knowledge_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    feedback_id = str(uuid.uuid4())
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.user_feedback (
                        feedback_id, response_id, knowledge_id, user_email,
                        feedback_type, rating, comment, metadata
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (response_id, user_email, feedback_type)
                    WHERE response_id IS NOT NULL
                    DO UPDATE SET
                        rating = EXCLUDED.rating,
                        comment = EXCLUDED.comment,
                        metadata = EXCLUDED.metadata,
                        created_at = now()
                    RETURNING feedback_id
                    """,
                    (
                        feedback_id,
                        response_id,
                        knowledge_id,
                        user_email,
                        feedback_type,
                        rating,
                        comment,
                        Jsonb(metadata or {}),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return str(row[0]) if row else feedback_id
    except Exception as exc:
        LOGGER.warning("insert_feedback failed: %s", exc)
        return None


def get_response(response_id: str) -> dict[str, Any] | None:
    cols = [
        "response_id", "session_id", "user_email", "query_text", "answer_text",
        "model_provider", "model_name", "model_role", "intent", "project_codes",
        "citation_count", "has_citations", "pipeline_status", "metadata", "created_at",
    ]
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {', '.join(cols)} FROM platform.ai_responses WHERE response_id = %s",
                    (response_id,),
                )
                row = cur.fetchone()
        return _row_to_dict(row, cols) if row else None
    except Exception as exc:
        LOGGER.warning("get_response failed: %s", exc)
        return None


def list_feedback_for_response(response_id: str) -> list[dict[str, Any]]:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT feedback_type, rating, comment, user_email, created_at
                    FROM platform.user_feedback
                    WHERE response_id = %s
                    ORDER BY created_at DESC
                    """,
                    (response_id,),
                )
                rows = cur.fetchall()
        return [
            {
                "feedback_type": r[0],
                "rating": r[1],
                "comment": r[2],
                "user_email": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
    except Exception as exc:
        LOGGER.warning("list_feedback_for_response failed: %s", exc)
        return []


def search_knowledge(
    query: str,
    *,
    status_filter: list[str] | None = None,
    limit: int = 20,
    exclude_rejected: bool = True,
) -> list[dict[str, Any]]:
    tokens = [t for t in re_tokenize(query) if len(t) >= 3]
    if not tokens and not query.strip():
        return []

    statuses = status_filter or [
        StorageStatus.VERIFIED.value,
        StorageStatus.DRAFT.value,
        StorageStatus.LOW_CONFIDENCE.value,
    ]
    if exclude_rejected:
        statuses = [s for s in statuses if s not in (StorageStatus.REJECTED.value,)]

    pattern = "%" + "%".join(tokens[:6]) + "%" if tokens else f"%{query.strip()}%"
    cols = [
        "knowledge_id", "response_id", "claim_id", "title", "content",
        "storage_status", "confidence_score", "has_citation", "entity_type",
        "classification", "version", "metadata", "created_at",
    ]
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {', '.join(cols)}
                    FROM platform.knowledge_items
                    WHERE storage_status = ANY(%s)
                      AND (title ILIKE %s OR content ILIKE %s)
                    ORDER BY confidence_score DESC, created_at DESC
                    LIMIT %s
                    """,
                    (statuses, pattern, pattern, limit),
                )
                rows = cur.fetchall()
        return [_row_to_dict(r, cols) for r in rows]
    except Exception as exc:
        LOGGER.warning("search_knowledge failed: %s", exc)
        return []


def list_graph_edges(
    *,
    subject_name: str | None = None,
    object_name: str | None = None,
    status_filter: list[str] | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    statuses = status_filter or [
        StorageStatus.VERIFIED.value,
        StorageStatus.DRAFT.value,
        StorageStatus.LOW_CONFIDENCE.value,
    ]
    cols = [
        "edge_id", "knowledge_id", "subject_name", "subject_type", "relation_type",
        "object_name", "object_type", "confidence_score", "evidence_text",
        "storage_status", "version", "metadata", "created_at",
    ]
    clauses = ["storage_status = ANY(%s)"]
    params: list[Any] = [statuses]
    if subject_name:
        clauses.append("subject_name ILIKE %s")
        params.append(f"%{subject_name}%")
    if object_name:
        clauses.append("object_name ILIKE %s")
        params.append(f"%{object_name}%")
    params.append(limit)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {', '.join(cols)}
                    FROM platform.knowledge_graph_edges
                    WHERE {' AND '.join(clauses)}
                    ORDER BY confidence_score DESC, created_at DESC
                    LIMIT %s
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()
        return [_row_to_dict(r, cols) for r in rows]
    except Exception as exc:
        LOGGER.warning("list_graph_edges failed: %s", exc)
        return []


def get_knowledge_item(knowledge_id: str) -> dict[str, Any] | None:
    cols = [
        "knowledge_id", "response_id", "claim_id", "title", "content",
        "storage_status", "confidence_score", "has_citation", "entity_type",
        "classification", "version", "supersedes_id", "contradiction_flags",
        "metadata", "created_at", "deprecated_at",
    ]
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {', '.join(cols)} FROM platform.knowledge_items WHERE knowledge_id = %s",
                    (knowledge_id,),
                )
                row = cur.fetchone()
        return _row_to_dict(row, cols) if row else None
    except Exception as exc:
        LOGGER.warning("get_knowledge_item failed: %s", exc)
        return None


def re_tokenize(query: str) -> list[str]:
    import re
    return re.findall(r"[a-z0-9]{3,}", (query or "").lower())
