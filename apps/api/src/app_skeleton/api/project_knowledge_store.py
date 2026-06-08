"""Project workspace knowledge — Postgres rag.* + Qdrant doc_chunks (corpus=project_workspace)."""
from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import psycopg
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app_skeleton.api.embedding_service import embed_text, embedding_dim
from app_skeleton.api.llm_client import LLMClient
from app_skeleton.api.qdrant_vectors import (
    DOC_CHUNKS_COLLECTION,
    TEXT_VECTOR_NAME,
    ensure_doc_chunks_collection,
    get_qdrant_client,
)
from app_skeleton.api.vector_indexer import upsert_text_chunks

LOGGER = logging.getLogger(__name__)

PROJECT_CORPUS = "project_workspace"
SOURCE_TYPE_PROJECT = "project_workspace_document"


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


def _qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "http://localhost:6333").strip()


def _tokenize(query: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{3,}", (query or "").lower()) if t]


def upsert_chunks_to_qdrant(
    *,
    document_code: str,
    title: str,
    project_code: str,
    relative_path: str,
    chunks: list[dict[str, Any]],
    document_id: str,
    qdrant: QdrantClient | None = None,
    llm: LLMClient | None = None,
) -> int:
    """Embed and upsert project workspace chunks into doc_chunks collection."""
    if not chunks:
        return 0
    llm = llm or LLMClient()
    dim = embedding_dim()
    client = qdrant or get_qdrant_client(_qdrant_url())
    ensure_doc_chunks_collection(client)

    points_data: list[dict[str, Any]] = []
    for chunk in chunks:
        text = (chunk.get("chunk_text") or "").strip()
        if len(text) < 8:
            continue
        chunk_uid = chunk.get("chunk_uid") or ""
        if not chunk_uid:
            continue
        payload = {
            "schema_version": 1,
            "corpus": PROJECT_CORPUS,
            "scope": "project",
            "source_type": SOURCE_TYPE_PROJECT,
            "document_id": document_id,
            "document_code": document_code,
            "title": title,
            "chunk_id": chunk_uid,
            "chunk_index": chunk.get("chunk_index", 0),
            "project_code": project_code,
            "relative_path": relative_path,
            "text_preview": text[:2000],
            "text": text[:8000],
            "embedding_model": os.getenv("EMBEDDING_PROVIDER", "hash"),
            "embedding_dimension": dim,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        points_data.append({"chunk_uid": chunk_uid, "text": text, "payload": payload})

    if not points_data:
        return 0
    return upsert_text_chunks(client, points_data, collection=DOC_CHUNKS_COLLECTION, llm=llm)


def search_project_knowledge(
    query: str,
    *,
    project_codes: list[str] | None = None,
    limit: int = 12,
    qdrant: QdrantClient | None = None,
    llm: LLMClient | None = None,
) -> list[dict[str, Any]]:
    """Semantic + keyword search over project_workspace corpus."""
    query = (query or "").strip()
    if len(query) < 2:
        return []

    limit = max(1, min(int(limit or 12), 40))
    hits: list[dict[str, Any]] = []
    llm = llm or LLMClient()

    try:
        client = qdrant or get_qdrant_client(_qdrant_url())
        vector = embed_text(query, llm=llm)
        must = [models.FieldCondition(key="corpus", match=models.MatchValue(value=PROJECT_CORPUS))]
        if project_codes:
            should = [
                models.FieldCondition(key="project_code", match=models.MatchValue(value=code))
                for code in project_codes[:8]
            ]
            query_filter = models.Filter(
                must=must,
                should=should,
            )
        else:
            query_filter = models.Filter(must=must)

        response = client.query_points(
            collection_name=DOC_CHUNKS_COLLECTION,
            query=vector,
            using=TEXT_VECTOR_NAME,
            query_filter=query_filter,
            limit=limit * 2,
        )
        for rank, point in enumerate(getattr(response, "points", []) or [], start=1):
            p = point.payload or {}
            if p.get("corpus") != PROJECT_CORPUS:
                continue
            hits.append(_format_hit(rank, float(point.score or 0), p))
            if len(hits) >= limit:
                return hits
    except Exception as exc:
        LOGGER.warning("Qdrant project search failed, using Postgres: %s", exc)

    if len(hits) < limit:
        seen = {h["chunk_uid"] for h in hits}
        hits.extend(_search_postgres(query, project_codes=project_codes, limit=limit - len(hits), seen=seen))
    return hits[:limit]


def _format_hit(rank: int, score: float, payload: dict[str, Any]) -> dict[str, Any]:
    rel = payload.get("relative_path") or ""
    title = payload.get("title") or rel.split("/")[-1] or "Project document"
    text = payload.get("text_preview") or payload.get("text") or ""
    code = payload.get("project_code") or ""
    return {
        "rank": rank,
        "score": round(score, 4),
        "chunk_uid": str(payload.get("chunk_id") or ""),
        "document_code": payload.get("document_code"),
        "project_code": code,
        "title": title,
        "relative_path": rel,
        "excerpt": text[:1200],
        "source_type": SOURCE_TYPE_PROJECT,
        "corpus": PROJECT_CORPUS,
    }


def _search_postgres(
    query: str,
    *,
    project_codes: list[str] | None,
    limit: int,
    seen: set[str],
) -> list[dict[str, Any]]:
    tokens = _tokenize(query)
    if not tokens:
        return []

    score_expr = " + ".join(
        ["CASE WHEN lower(dc.chunk_text) LIKE %s THEN 1 ELSE 0 END" for _ in tokens]
    )
    clauses = ["ds.metadata->>'corpus' = %s"]
    bind: list[Any] = [PROJECT_CORPUS]
    if project_codes:
        clauses.append("ds.metadata->>'project_code' = ANY(%s)")
        bind.append(project_codes)
    bind.extend([f"%{t}%" for t in tokens])
    bind.extend([f"%{t}%" for t in tokens])
    bind.append(limit)

    sql = f"""
        SELECT dc.chunk_uid, dc.chunk_text, ds.document_code, ds.title, ds.metadata,
               ({score_expr}) AS relevance
        FROM rag.document_chunk dc
        JOIN rag.document_source ds ON ds.document_id = dc.document_id
        WHERE {' AND '.join(clauses)}
          AND ({score_expr}) > 0
        ORDER BY relevance DESC
        LIMIT %s;
    """

    rows: list[tuple] = []
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(bind))
                rows = cur.fetchall()
    except Exception as exc:
        LOGGER.debug("Postgres project search failed: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        chunk_uid, text, doc_code, title, metadata, relevance = row
        if chunk_uid in seen:
            continue
        meta = metadata if isinstance(metadata, dict) else {}
        out.append(
            _format_hit(
                i,
                float(relevance or 0) * 0.15,
                {
                    "chunk_id": chunk_uid,
                    "document_code": doc_code,
                    "title": title,
                    "relative_path": meta.get("relative_path"),
                    "project_code": meta.get("project_code"),
                    "text_preview": text,
                },
            )
        )
    return out
