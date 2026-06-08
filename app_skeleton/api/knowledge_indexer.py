"""Unified Postgres rag.* + Qdrant write path for knowledge chunks."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import psycopg
from qdrant_client import QdrantClient

from app_skeleton.api.platform_flags import knowledge_indexer_enabled, platform_chunk_write_enabled
from app_skeleton.api.qdrant_collections import DOC_CHUNKS
from app_skeleton.api.qdrant_vectors import get_qdrant_client
from app_skeleton.api.vector_indexer import upsert_text_chunks

LOGGER = logging.getLogger(__name__)


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


def write_chunks(
    *,
    document_code: str,
    title: str,
    source_type: str,
    metadata: dict[str, Any],
    chunks: list[dict[str, Any]],
    qdrant: QdrantClient | None = None,
    llm: Any | None = None,
    collection: str | None = None,
) -> dict[str, Any]:
    """Write chunks to rag.document_source + rag.document_chunk + Qdrant."""
    if not knowledge_indexer_enabled():
        return {"enabled": False, "chunks_written": 0, "vectors_upserted": 0}

    if not chunks:
        return {"enabled": True, "chunks_written": 0, "vectors_upserted": 0}

    collection = collection or DOC_CHUNKS
    vectors_upserted = 0
    document_id: str | None = None

    with psycopg.connect(_db_conn(), connect_timeout=12) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rag.document_source (document_code, title, source_type, metadata)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (document_code) DO UPDATE SET
                    title = EXCLUDED.title,
                    source_type = EXCLUDED.source_type,
                    metadata = EXCLUDED.metadata
                RETURNING document_id;
                """,
                (document_code, title, source_type, json.dumps(metadata)),
            )
            document_id = str(cur.fetchone()[0])

            for chunk in chunks:
                cur.execute(
                    """
                    INSERT INTO rag.document_chunk (
                        document_id, chunk_index, chunk_uid, chunk_text, token_count, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_uid) DO UPDATE SET
                        chunk_text = EXCLUDED.chunk_text,
                        token_count = EXCLUDED.token_count,
                        metadata = EXCLUDED.metadata;
                    """,
                    (
                        document_id,
                        chunk.get("chunk_index", 0),
                        chunk["chunk_uid"],
                        chunk.get("chunk_text") or chunk.get("text") or "",
                        chunk.get("token_count") or 0,
                        json.dumps(chunk.get("metadata") or {}),
                    ),
                )
            conn.commit()

    points_data = []
    for chunk in chunks:
        text = chunk.get("chunk_text") or chunk.get("text") or ""
        chunk_uid = chunk.get("chunk_uid") or ""
        if not chunk_uid or len(text.strip()) < 8:
            continue
        points_data.append({
            "chunk_uid": chunk_uid,
            "text": text,
            "payload": {
                "document_code": document_code,
                "document_id": document_id,
                "title": title,
                "chunk_index": chunk.get("chunk_index", 0),
                **metadata,
            },
        })

    if points_data:
        try:
            client = qdrant or get_qdrant_client()
            vectors_upserted = upsert_text_chunks(client, points_data, collection=collection, llm=llm)
        except Exception as exc:
            LOGGER.warning("Qdrant upsert via knowledge_indexer failed: %s", exc)

    return {
        "enabled": True,
        "document_id": document_id,
        "document_code": document_code,
        "chunks_written": len(chunks),
        "vectors_upserted": vectors_upserted,
        "platform_chunk_write": platform_chunk_write_enabled(),
    }


# Re-export for backward-compatible imports
__all__ = ["knowledge_indexer_enabled", "platform_chunk_write_enabled", "write_chunks"]
