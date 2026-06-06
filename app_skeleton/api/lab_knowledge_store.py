"""Canonical lab knowledge indexing: Postgres rag.* + Qdrant doc_chunks.

Hard rule:
- corpus=lab_operations → assimilated into app database (this module). No file streaming UI.
- corpus=project_workspace → project folder streaming (project_processor / project-files API).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app_skeleton.api import document_extraction as de
from app_skeleton.api.database_sections import DATABASE_SECTIONS, section_root
from app_skeleton.api.database_processor import (
    _iter_chunks_from_disk,
    get_section_record,
    load_processed_section,
)
from app_skeleton.api.llm_client import LLMClient
from app_skeleton.api.paths import DATABASE_ROOT

LOGGER = logging.getLogger(__name__)

LAB_CORPUS = "lab_operations"
SOURCE_TYPE_LAB = "lab_policy_document"
COLLECTION_DOC_CHUNKS = "doc_chunks"
EMBEDDING_DIM = 384
SCHEMA_VERSION = 1


def _db_conn():
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


def _stable_document_code(section_id: str, relative_path: str) -> str:
    norm = relative_path.strip().lstrip("/").replace("\\", "/")
    digest = hashlib.sha256(f"{section_id}:{norm}".encode("utf-8")).hexdigest()[:16]
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", norm)[-80:]
    return f"lab::{section_id}::{digest}::{safe}"


def _chunk_uid(document_code: str, chunk_index: int) -> str:
    return f"{document_code}::chunk_{chunk_index:04d}"


def _qdrant_point_id(chunk_uid: str) -> str:
    return hashlib.md5(chunk_uid.encode("utf-8")).hexdigest()


def _tokenize(query: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{3,}", (query or "").lower()) if t]


def _canonical_metadata(
    *,
    section_id: str,
    section_label: str,
    relative_path: str,
    absolute_path: str,
    document_kind: str,
    sha256: str | None,
    extractor: str | None,
    file_extension: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "corpus": LAB_CORPUS,
        "section_id": section_id,
        "section_label": section_label,
        "relative_path": relative_path,
        "absolute_disk_path": absolute_path,
        "document_kind": document_kind,
        "sha256": sha256,
        "extractor": extractor,
        "file_extension": file_extension,
        "where_to_find": f"{section_label} → {relative_path}",
        "database_root": str(DATABASE_ROOT),
    }


def _canonical_qdrant_payload(
    *,
    document_id: str,
    chunk_id: str,
    chunk_uid: str,
    document_code: str,
    title: str,
    section_id: str,
    section_label: str,
    relative_path: str,
    chunk_index: int,
    text_preview: str,
    document_kind: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "corpus": LAB_CORPUS,
        "scope": "lab",
        "source_type": SOURCE_TYPE_LAB,
        "document_id": document_id,
        "source_file_id": relative_path,
        "chunk_id": chunk_uid,
        "chunk_index": chunk_index,
        "document_code": document_code,
        "title": title,
        "text_preview": text_preview[:2000],
        "text": text_preview[:8000],
        "section_id": section_id,
        "section_label": section_label,
        "relative_path": relative_path,
        "where_to_find": f"{section_label} → {relative_path}",
        "document_kind": document_kind,
        "project_code": None,
        "allowed_project_codes": [],
        "modality": ["lab_operations"],
        "sensitivity_level": "internal",
        "contains_patient_level_data": False,
        "contains_direct_identifier": False,
        "embedding_model": "llm_client_hashed_embed",
        "embedding_dimension": EMBEDDING_DIM,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _stored_checksum(cur, document_code: str) -> str | None:
    cur.execute(
        """
        SELECT metadata->>'sha256'
        FROM rag.document_source
        WHERE document_code = %s AND status = 'active';
        """,
        (document_code,),
    )
    row = cur.fetchone()
    if not row or not row[0]:
        return None
    return str(row[0])


def _upsert_document_source(
    cur,
    *,
    document_code: str,
    title: str,
    section_id: str,
    meta: dict[str, Any],
) -> uuid.UUID:
    cur.execute(
        """
        INSERT INTO rag.document_source (
            document_code, title, source_type, project_id,
            sensitivity_level, status, metadata
        ) VALUES (%s, %s, %s, NULL, 'internal', 'active', %s)
        ON CONFLICT (document_code) DO UPDATE SET
            title = EXCLUDED.title,
            source_type = EXCLUDED.source_type,
            metadata = EXCLUDED.metadata,
            status = 'active'
        RETURNING document_id;
        """,
        (document_code, title, SOURCE_TYPE_LAB, psycopg.types.json.Jsonb(meta)),
    )
    row = cur.fetchone()
    return row[0]


def _replace_document_chunks(cur, document_id: uuid.UUID, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cur.execute("DELETE FROM rag.document_chunk WHERE document_id = %s;", (document_id,))
    stored = []
    for idx, chunk in enumerate(chunks):
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        chunk_uid = chunk.get("chunk_id") or _chunk_uid(str(document_id), idx)
        section_path = chunk.get("source_file") or chunk.get("section_path") or ""
        cur.execute(
            """
            INSERT INTO rag.document_chunk (
                document_id, chunk_index, chunk_uid, section_path,
                chunk_text, token_count, sensitivity_level, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, 'internal', %s)
            RETURNING chunk_id;
            """,
            (
                document_id,
                idx,
                chunk_uid,
                section_path,
                text,
                chunk.get("word_count") or len(text.split()),
                psycopg.types.json.Jsonb({
                    "start_char": chunk.get("start_char"),
                    "end_char": chunk.get("end_char"),
                    "char_count": chunk.get("char_count"),
                }),
            ),
        )
        chunk_row_id = cur.fetchone()[0]
        stored.append({
            **chunk,
            "chunk_uid": chunk_uid,
            "db_chunk_id": str(chunk_row_id),
            "chunk_index": idx,
        })
    return stored


def ingest_section_to_database(
    section_id: str,
    *,
    qdrant: QdrantClient | None = None,
    llm: LLMClient | None = None,
    refresh_extract: bool = False,
) -> dict[str, Any]:
    """Extract (if needed), then assimilate section into rag.* and Qdrant."""
    if section_id not in DATABASE_SECTIONS:
        raise ValueError(f"Unknown section: {section_id}")

    meta_section = DATABASE_SECTIONS[section_id]
    root = section_root(section_id)

    twin = get_section_record(section_id, refresh=refresh_extract)
    if not twin:
        raise FileNotFoundError(f"No processed twin for {section_id}")

    chunks_by_path: dict[str, list[dict[str, Any]]] = {}
    for chunk in _iter_chunks_from_disk(section_id):
        path = (chunk.get("source_file") or "").replace("\\", "/")
        if path:
            chunks_by_path.setdefault(path, []).append(chunk)

    llm = llm or LLMClient()
    qdrant = qdrant or QdrantClient(url=_qdrant_url())
    _ensure_qdrant_collection(qdrant)

    stats = {
        "section_id": section_id,
        "documents_upserted": 0,
        "chunks_indexed": 0,
        "vectors_upserted": 0,
        "skipped_empty": 0,
        "skipped_unchanged": 0,
        "errors": [],
    }

    doc_index = {d["path"]: d for d in twin.get("document_index") or [] if d.get("path")}

    with psycopg.connect(_db_conn(), connect_timeout=10) as conn:
        with conn.cursor() as cur:
            job_id = _start_embedding_job(cur, section_id)

            for rel_path, doc_meta in sorted(doc_index.items()):
                file_chunks = chunks_by_path.get(rel_path, [])
                if not file_chunks:
                    excerpt = (doc_meta.get("excerpt") or "").strip()
                    if not excerpt:
                        stats["skipped_empty"] += 1
                        continue
                    file_chunks = [{
                        "chunk_id": _chunk_uid(rel_path, 0),
                        "source_file": rel_path,
                        "chunk_index": 0,
                        "text": excerpt,
                        "word_count": doc_meta.get("word_count"),
                    }]

                document_code = _stable_document_code(section_id, rel_path)
                new_checksum = (doc_meta.get("sha256") or "").strip() or None
                if new_checksum:
                    prior = _stored_checksum(cur, document_code)
                    if prior and prior == new_checksum:
                        stats["skipped_unchanged"] += 1
                        continue

                title = doc_meta.get("title") or Path(rel_path).name
                abs_path = str((root / rel_path).resolve())
                metadata = _canonical_metadata(
                    section_id=section_id,
                    section_label=meta_section["label"],
                    relative_path=rel_path,
                    absolute_path=abs_path,
                    document_kind=doc_meta.get("document_kind") or "document",
                    sha256=doc_meta.get("sha256"),
                    extractor=doc_meta.get("extractor"),
                    file_extension=doc_meta.get("extension") or Path(rel_path).suffix,
                )

                try:
                    document_id = _upsert_document_source(
                        cur,
                        document_code=document_code,
                        title=title,
                        section_id=section_id,
                        meta=metadata,
                    )
                    stored_chunks = _replace_document_chunks(cur, document_id, file_chunks)
                    stats["documents_upserted"] += 1
                    stats["chunks_indexed"] += len(stored_chunks)

                    points = []
                    for sc in stored_chunks:
                        text = sc.get("text") or ""
                        chunk_uid = sc["chunk_uid"]
                        payload = _canonical_qdrant_payload(
                            document_id=str(document_id),
                            chunk_id=sc.get("db_chunk_id", ""),
                            chunk_uid=chunk_uid,
                            document_code=document_code,
                            title=title,
                            section_id=section_id,
                            section_label=meta_section["label"],
                            relative_path=rel_path,
                            chunk_index=sc["chunk_index"],
                            text_preview=text,
                            document_kind=metadata["document_kind"],
                        )
                        vector = llm.embed(text[:4000], dim=EMBEDDING_DIM)
                        qid = _qdrant_point_id(chunk_uid)
                        points.append(models.PointStruct(
                            id=qid,
                            vector={"text": vector},
                            payload=payload,
                        ))
                        cur.execute(
                            """
                            INSERT INTO rag.vector_point_registry (
                                embedding_job_id, collection_name, qdrant_point_id,
                                source_type, source_uuid, chunk_id, project_id,
                                embedding_model, embedding_dimension, payload, status
                            ) VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, 'active')
                            ON CONFLICT (collection_name, qdrant_point_id) DO UPDATE SET
                                payload = EXCLUDED.payload,
                                chunk_id = EXCLUDED.chunk_id,
                                status = 'active';
                            """,
                            (
                                job_id,
                                COLLECTION_DOC_CHUNKS,
                                qid,
                                SOURCE_TYPE_LAB,
                                document_id,
                                uuid.UUID(sc["db_chunk_id"]),
                                "llm_client_hashed_embed",
                                EMBEDDING_DIM,
                                psycopg.types.json.Jsonb(payload),
                            ),
                        )

                    if points:
                        qdrant.upsert(collection_name=COLLECTION_DOC_CHUNKS, points=points)
                        stats["vectors_upserted"] += len(points)

                except Exception as exc:
                    stats["errors"].append({"path": rel_path, "error": str(exc)[:300]})
                    LOGGER.exception("Failed to index %s", rel_path)

            _finish_embedding_job(cur, job_id, stats)
            conn.commit()

    return stats


def ingest_all_lab_sections(**kwargs) -> dict[str, Any]:
    results = []
    errors = []
    for section_id in DATABASE_SECTIONS:
        try:
            stats = ingest_section_to_database(section_id, **kwargs)
            results.append(stats)
        except Exception as exc:
            errors.append({"section_id": section_id, "error": str(exc)})
    return {
        "corpus": LAB_CORPUS,
        "sections_processed": len(results),
        "results": results,
        "errors": errors,
        "totals": {
            "documents": sum(r.get("documents_upserted", 0) for r in results),
            "chunks": sum(r.get("chunks_indexed", 0) for r in results),
            "vectors": sum(r.get("vectors_upserted", 0) for r in results),
        },
    }


def search_lab_knowledge(
    query: str,
    *,
    section_id: str | None = None,
    limit: int = 15,
    qdrant: QdrantClient | None = None,
    llm: LLMClient | None = None,
) -> list[dict[str, Any]]:
    """Search canonical lab index. Returns citation + excerpt + where_to_find."""
    query = (query or "").strip()
    if len(query) < 2:
        return []

    limit = max(1, min(int(limit or 15), 50))
    hits: list[dict[str, Any]] = []

    llm = llm or LLMClient()
    try:
        qdrant = qdrant or QdrantClient(url=_qdrant_url())
        vector = llm.embed(query, dim=EMBEDDING_DIM)
        must = [models.FieldCondition(key="corpus", match=models.MatchValue(value=LAB_CORPUS))]
        if section_id:
            must.append(models.FieldCondition(key="section_id", match=models.MatchValue(value=section_id)))
        response = qdrant.query_points(
            collection_name=COLLECTION_DOC_CHUNKS,
            query=vector,
            using="text",
            query_filter=models.Filter(must=must),
            limit=limit * 2,
        )
        for rank, point in enumerate(getattr(response, "points", []) or [], start=1):
            p = point.payload or {}
            if p.get("corpus") != LAB_CORPUS:
                continue
            hits.append(_format_search_hit(rank, float(point.score or 0), p, point.id))
            if len(hits) >= limit:
                return hits
    except Exception as exc:
        LOGGER.warning("Qdrant lab search failed, using Postgres: %s", exc)

    if len(hits) < limit:
        hits.extend(_search_postgres(query, section_id=section_id, limit=limit - len(hits), seen={h["chunk_uid"] for h in hits}))

    return hits[:limit]


def _search_postgres(
    query: str,
    *,
    section_id: str | None,
    limit: int,
    seen: set[str],
) -> list[dict[str, Any]]:
    tokens = _tokenize(query)
    if not tokens:
        return []

    score_params = [f"%{tok}%" for tok in tokens]
    where_score = " + ".join(
        ["CASE WHEN lower(dc.chunk_text) LIKE %s THEN 1 ELSE 0 END" for _ in tokens]
    )
    section_clause = "AND ds.metadata->>'section_id' = %s" if section_id else ""
    bind: list[Any] = [LAB_CORPUS]
    if section_id:
        bind.append(section_id)
    bind.extend(score_params)
    bind.extend(score_params)
    bind.append(limit)

    sql = f"""
        SELECT
            dc.chunk_uid, dc.chunk_text, dc.chunk_index, dc.section_path,
            ds.document_id, ds.document_code, ds.title, ds.metadata,
            ({where_score}) AS relevance
        FROM rag.document_chunk dc
        JOIN rag.document_source ds ON ds.document_id = dc.document_id
        WHERE ds.metadata->>'corpus' = %s
        {section_clause}
          AND ({where_score}) > 0
        ORDER BY relevance DESC
        LIMIT %s;
    """

    rows = []
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, bind)
                rows = cur.fetchall()
    except Exception as exc:
        LOGGER.warning("Postgres lab search failed: %s", exc)
        return []

    out = []
    for i, row in enumerate(rows, start=1):
        chunk_uid, text, chunk_index, section_path, doc_id, doc_code, title, metadata, relevance = row
        if chunk_uid in seen:
            continue
        meta = metadata if isinstance(metadata, dict) else {}
        payload = {
            "chunk_id": chunk_uid,
            "chunk_index": chunk_index,
            "relative_path": section_path or meta.get("relative_path"),
            "section_id": meta.get("section_id"),
            "section_label": meta.get("section_label"),
            "title": title,
            "document_code": doc_code,
            "where_to_find": meta.get("where_to_find"),
            "text_preview": text[:2000],
            "text": text[:8000],
        }
        out.append(_format_search_hit(i, float(relevance), payload, chunk_uid))
    return out


def _format_search_hit(rank: int, score: float, payload: dict[str, Any], point_id: Any) -> dict[str, Any]:
    section_label = payload.get("section_label") or payload.get("section_id") or "Lab"
    rel = payload.get("relative_path") or payload.get("source_file_id") or ""
    title = payload.get("title") or rel.split("/")[-1] or "Document"
    where = payload.get("where_to_find") or f"{section_label} → {rel}"
    text = payload.get("text_preview") or payload.get("text") or ""
    return {
        "rank": rank,
        "score": round(score, 4),
        "chunk_uid": str(payload.get("chunk_id") or point_id),
        "document_code": payload.get("document_code"),
        "document_id": payload.get("document_id"),
        "section_id": payload.get("section_id"),
        "section_label": section_label,
        "title": title,
        "relative_path": rel,
        "where_to_find": where,
        "citation": where,
        "excerpt": text[:1200],
        "full_text": text[:8000],
        "source_type": SOURCE_TYPE_LAB,
        "corpus": LAB_CORPUS,
    }


def get_lab_index_stats() -> dict[str, Any]:
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT ds.document_id), COUNT(dc.chunk_id)
                    FROM rag.document_source ds
                    LEFT JOIN rag.document_chunk dc ON dc.document_id = ds.document_id
                    WHERE ds.metadata->>'corpus' = %s;
                    """,
                    (LAB_CORPUS,),
                )
                docs, chunks = cur.fetchone()
                cur.execute(
                    """
                    SELECT ds.metadata->>'section_id' AS sid, COUNT(dc.chunk_id) AS n
                    FROM rag.document_source ds
                    JOIN rag.document_chunk dc ON dc.document_id = ds.document_id
                    WHERE ds.metadata->>'corpus' = %s
                    GROUP BY sid ORDER BY sid;
                    """,
                    (LAB_CORPUS,),
                )
                by_section = [{"section_id": r[0], "chunks": r[1]} for r in cur.fetchall()]
                return {
                    "corpus": LAB_CORPUS,
                    "documents": docs or 0,
                    "chunks": chunks or 0,
                    "by_section": by_section,
                }
    except Exception as exc:
        return {"corpus": LAB_CORPUS, "error": str(exc), "documents": 0, "chunks": 0}


def _qdrant_url() -> str:
    import os
    return os.getenv("QDRANT_URL", "http://localhost:6333")


def _ensure_qdrant_collection(client: QdrantClient) -> None:
    from app_skeleton.api.qdrant_vectors import ensure_doc_chunks_collection

    ensure_doc_chunks_collection(client)


def _start_embedding_job(cur, section_id: str) -> uuid.UUID:
    code = f"lab_ingest_{section_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    cur.execute(
        """
        INSERT INTO rag.embedding_job (
            job_code, embedding_model, embedding_dimension, distance_metric,
            collection_name, started_at, status, config
        ) VALUES (%s, %s, %s, 'cosine', %s, now(), 'running', %s)
        RETURNING embedding_job_id;
        """,
        (
            code,
            "llm_client_hashed_embed",
            EMBEDDING_DIM,
            COLLECTION_DOC_CHUNKS,
            psycopg.types.json.Jsonb({"section_id": section_id, "corpus": LAB_CORPUS}),
        ),
    )
    return cur.fetchone()[0]


def _finish_embedding_job(cur, job_id: uuid.UUID, stats: dict[str, Any]) -> None:
    cur.execute(
        """
        UPDATE rag.embedding_job
        SET finished_at = now(), status = 'success', config = config || %s::jsonb
        WHERE embedding_job_id = %s;
        """,
        (psycopg.types.json.Jsonb({"stats": stats}), job_id),
    )


def _cli() -> int:
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(description="Ingest lab folders into canonical rag.* database.")
    parser.add_argument("--section")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--refresh-extract", action="store_true", help="Re-scan files on disk before ingest")
    args = parser.parse_args()
    if args.all:
        print(_json.dumps(ingest_all_lab_sections(refresh_extract=args.refresh_extract), indent=2, default=str))
        return 0
    if args.section:
        print(_json.dumps(
            ingest_section_to_database(args.section, refresh_extract=args.refresh_extract),
            indent=2,
            default=str,
        ))
        return 0
    parser.error("Use --all or --section")
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
