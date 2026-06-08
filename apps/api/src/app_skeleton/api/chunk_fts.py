"""Postgres full-text search over rag.document_chunk (hybrid retrieval)."""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import psycopg

LOGGER = logging.getLogger(__name__)


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


def fts_enabled() -> bool:
    return os.getenv("CHUNK_FTS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def _sanitize_tsquery(query: str) -> str:
    """Build a safe plainto_tsquery input (strip special chars)."""
    cleaned = re.sub(r"[^\w\s\u00c0-\uffff-]", " ", query or "")
    return " ".join(cleaned.split())[:500]


def search_chunks_fts(
    query: str,
    *,
    corpus: str | None = "lab_operations",
    section_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """BM25-like ranked chunk search via Postgres tsvector."""
    if not fts_enabled():
        return []
    q = _sanitize_tsquery(query)
    if len(q) < 2:
        return []

    limit = max(1, min(int(limit or 20), 50))
    clauses = ["ds.metadata->>'corpus' = %s"]
    params: list[Any] = [corpus or "lab_operations"]
    if section_id:
        clauses.append("ds.metadata->>'section_id' = %s")
        params.append(section_id)
    params.extend([q, q, limit])

    sql = f"""
        SELECT
            dc.chunk_uid,
            dc.chunk_text,
            dc.chunk_index,
            dc.section_path,
            ds.document_id,
            ds.document_code,
            ds.title,
            ds.metadata,
            ts_rank(
                to_tsvector('english', coalesce(dc.chunk_text, '')),
                plainto_tsquery('english', %s)
            ) AS rank
        FROM rag.document_chunk dc
        JOIN rag.document_source ds ON ds.document_id = dc.document_id
        WHERE {' AND '.join(clauses)}
          AND to_tsvector('english', coalesce(dc.chunk_text, ''))
              @@ plainto_tsquery('english', %s)
        ORDER BY rank DESC
        LIMIT %s;
    """

    rows: list[tuple] = []
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
    except Exception as exc:
        LOGGER.debug("Chunk FTS unavailable (migration 144?): %s", exc)
        return []

    hits: list[dict[str, Any]] = []
    for row in rows:
        chunk_uid, text, chunk_index, section_path, doc_id, doc_code, title, metadata, rank = row
        meta = metadata if isinstance(metadata, dict) else {}
        hits.append(
            {
                "chunk_uid": chunk_uid,
                "chunk_text": text,
                "chunk_index": chunk_index,
                "section_path": section_path,
                "document_id": str(doc_id),
                "document_code": doc_code,
                "title": title,
                "metadata": meta,
                "score": float(rank or 0.0),
                "engine": "postgres_fts",
            }
        )
    return hits
