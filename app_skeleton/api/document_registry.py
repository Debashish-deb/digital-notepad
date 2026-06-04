"""Unified document registry view (LUMI-W040)."""
from __future__ import annotations

import os
from typing import Any

import psycopg

LAB_CORPUS = "lab_operations"


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


def list_documents(
    *,
    corpus: str | None = None,
    section_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    corpus = corpus or LAB_CORPUS
    limit = max(1, min(limit, 200))
    clauses = ["ds.metadata->>'corpus' = %s"]
    params: list[Any] = [corpus]
    if section_id:
        clauses.append("ds.metadata->>'section_id' = %s")
        params.append(section_id)
    params.append(limit)
    sql = f"""
        SELECT
            ds.document_code,
            ds.title,
            ds.source_type,
            ds.sensitivity_level,
            ds.status,
            ds.metadata,
            COUNT(dc.chunk_id) AS chunk_count
        FROM rag.document_source ds
        LEFT JOIN rag.document_chunk dc ON dc.document_id = ds.document_id
        WHERE {' AND '.join(clauses)}
        GROUP BY ds.document_id
        ORDER BY ds.title
        LIMIT %s;
    """
    rows = []
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            for r in cur.fetchall():
                meta = r[5] if isinstance(r[5], dict) else {}
                rows.append({
                    "document_code": r[0],
                    "title": r[1],
                    "source_type": r[2],
                    "sensitivity_level": str(r[3]),
                    "status": str(r[4]),
                    "section_id": meta.get("section_id"),
                    "section_label": meta.get("section_label"),
                    "relative_path": meta.get("relative_path"),
                    "where_to_find": meta.get("where_to_find"),
                    "chunk_count": r[6],
                    "review_status": meta.get("review_status", "indexed"),
                    "project_code": meta.get("project_code"),
                    "folder_path": meta.get("folder_path"),
                })
    return rows
