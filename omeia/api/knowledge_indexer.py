"""Unified Postgres rag.* + Qdrant write path for knowledge chunks."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

import psycopg
from qdrant_client import QdrantClient

from omeia.api.chunking import chunk_text, normalize_chunks_for_indexer
from omeia.api.platform_flags import knowledge_indexer_enabled, platform_chunk_write_enabled
from omeia.api.qdrant_collections import DOC_CHUNKS
from omeia.api.qdrant_vectors import get_qdrant_client
from omeia.api.vector_indexer import upsert_text_chunks

LOGGER = logging.getLogger(__name__)


def _db_conn() -> str:
    from omeia.api.supabase_config import postgres_conn

    return postgres_conn()


def _stable_document_code(section_id: str, relative_path: str) -> str:
    norm = relative_path.strip().lstrip("/").replace("\\", "/")
    digest = hashlib.sha256(f"{section_id}:{norm}".encode("utf-8")).hexdigest()[:16]
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", norm)[-80:]
    return f"lab::{section_id}::{digest}::{safe}"


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

    prepared = normalize_chunks_for_indexer(chunks, document_code=document_code)
    if not prepared:
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

            for chunk in prepared:
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
    for chunk in prepared:
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
        "chunks_written": len(prepared),
        "vectors_upserted": vectors_upserted,
        "platform_chunk_write": platform_chunk_write_enabled(),
    }


def index_extraction_chunks(
    *,
    document_code: str,
    title: str,
    source_type: str,
    chunks: list[dict[str, Any]],
    metadata: dict[str, Any],
    qdrant: QdrantClient | None = None,
    llm: Any | None = None,
    collection: str | None = None,
) -> dict[str, Any]:
    """Canonical indexing entry for pre-chunked extraction results."""
    return write_chunks(
        document_code=document_code,
        title=title,
        source_type=source_type,
        metadata=metadata,
        chunks=chunks,
        qdrant=qdrant,
        llm=llm,
        collection=collection,
    )


def index_document_text(
    *,
    document_code: str,
    title: str,
    source_type: str,
    text: str,
    metadata: dict[str, Any],
    section_path: str = "",
    qdrant: QdrantClient | None = None,
    llm: Any | None = None,
    collection: str | None = None,
) -> dict[str, Any]:
    """Chunk via chunking.py facade, then index through write_chunks."""
    chunks = chunk_text(text, section_path=section_path or document_code)
    return index_extraction_chunks(
        document_code=document_code,
        title=title,
        source_type=source_type,
        chunks=chunks,
        metadata=metadata,
        qdrant=qdrant,
        llm=llm,
        collection=collection,
    )


def index_digitalization_chunks(
    *,
    document_code: str,
    title: str,
    source_type: str,
    chunks: list[Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Index digitalization DocumentChunk objects into rag.* + Qdrant."""
    payload = []
    for c in chunks:
        payload.append({
            "chunk_index": getattr(c, "chunk_index", 0),
            "chunk_id": getattr(c, "chunk_id", ""),
            "chunk_uid": getattr(c, "chunk_id", ""),
            "text": getattr(c, "text", ""),
            "token_count": getattr(c, "token_count", None),
            "metadata": getattr(c, "metadata", None) or {},
        })
    return index_extraction_chunks(
        document_code=document_code,
        title=title,
        source_type=source_type,
        chunks=payload,
        metadata=metadata,
    )


def index_vault_extraction(
    *,
    asset_id: str,
    filename: str,
    chunks: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Index vault extraction chunks under a stable rag document_code."""
    document_code = f"vault:{asset_id}"
    return index_extraction_chunks(
        document_code=document_code,
        title=filename or asset_id,
        source_type="vault_asset",
        chunks=chunks,
        metadata={"asset_id": asset_id, **metadata},
    )


def index_section_twin(
    *,
    section_id: str,
    section_label: str,
    twin: dict[str, Any],
    qdrant: QdrantClient | None = None,
    llm: Any | None = None,
) -> dict[str, Any]:
    """Index vector_chunks from a processed section twin JSON."""
    if not knowledge_indexer_enabled():
        return {"enabled": False, "documents_indexed": 0, "chunks_written": 0, "vectors_upserted": 0}

    chunks_by_path: dict[str, list[dict[str, Any]]] = {}
    for chunk in twin.get("vector_chunks") or []:
        path = (chunk.get("source_file") or "").replace("\\", "/")
        if path:
            chunks_by_path.setdefault(path, []).append(chunk)

    doc_index = {d["path"]: d for d in twin.get("document_index") or [] if d.get("path")}
    totals = {"enabled": True, "documents_indexed": 0, "chunks_written": 0, "vectors_upserted": 0}

    for rel_path, doc_meta in sorted(doc_index.items()):
        file_chunks = chunks_by_path.get(rel_path, [])
        if not file_chunks:
            excerpt = (doc_meta.get("excerpt") or "").strip()
            if not excerpt:
                continue
            file_chunks = chunk_text(excerpt, section_path=rel_path)

        document_code = _stable_document_code(section_id, rel_path)
        title = doc_meta.get("title") or rel_path
        metadata = {
            "section_id": section_id,
            "section_label": section_label,
            "relative_path": rel_path,
            "document_kind": doc_meta.get("document_kind") or "document",
            "sha256": doc_meta.get("sha256"),
            "corpus": "lab_operations",
        }
        result = index_extraction_chunks(
            document_code=document_code,
            title=title,
            source_type="lab_policy_document",
            chunks=file_chunks,
            metadata=metadata,
            qdrant=qdrant,
            llm=llm,
        )
        totals["documents_indexed"] += 1
        totals["chunks_written"] += result.get("chunks_written", 0)
        totals["vectors_upserted"] += result.get("vectors_upserted", 0)

    return totals


__all__ = [
    "knowledge_indexer_enabled",
    "platform_chunk_write_enabled",
    "write_chunks",
    "index_extraction_chunks",
    "index_document_text",
    "index_digitalization_chunks",
    "index_vault_extraction",
    "index_section_twin",
]
