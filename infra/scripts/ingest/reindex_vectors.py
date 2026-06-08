#!/usr/bin/env python3
"""Re-embed rag.document_chunk rows into Qdrant (after embedding model upgrade).

Usage:
  python scripts/ingest/reindex_vectors.py --dry-run
  python scripts/ingest/reindex_vectors.py --limit 500
  EMBEDDING_PROVIDER=ollama TEXT_EMBEDDING_DIM=768 python scripts/ingest/reindex_vectors.py

Requires: Postgres rag.* populated, Qdrant reachable, migration 144 optional for FTS.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import psycopg
from qdrant_client.http import models

from omeia.api.embedding_service import embed_text, embedding_dim, embedding_model_name, embedding_provider
from omeia.api.llm_client import LLMClient
from omeia.api.qdrant_vectors import (
    DOC_CHUNKS_COLLECTION,
    TEXT_VECTOR_NAME,
    ensure_named_text_collection,
    get_qdrant_client,
    stable_point_uuid,
    upsert_text_points,
)

LOGGER = logging.getLogger(__name__)


def _db_conn() -> str:
    from omeia.api.supabase_config import postgres_conn

    return postgres_conn()


def fetch_chunks(limit: int, offset: int) -> list[dict]:
    sql = """
        SELECT dc.chunk_uid, dc.chunk_text, dc.chunk_index, dc.section_path,
               ds.document_code, ds.title, ds.metadata
        FROM rag.document_chunk dc
        JOIN rag.document_source ds ON ds.document_id = dc.document_id
        ORDER BY ds.document_code, dc.chunk_index
        LIMIT %s OFFSET %s;
    """
    rows: list[dict] = []
    with psycopg.connect(_db_conn(), connect_timeout=12) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit, offset))
            for chunk_uid, text, chunk_index, section_path, doc_code, title, metadata in cur.fetchall():
                meta = metadata if isinstance(metadata, dict) else {}
                rows.append(
                    {
                        "chunk_uid": chunk_uid,
                        "chunk_text": text or "",
                        "chunk_index": chunk_index,
                        "section_path": section_path,
                        "document_code": doc_code,
                        "title": title,
                        "metadata": meta,
                    }
                )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=2000, help="Max chunks per batch (default 2000)")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--collection", default=DOC_CHUNKS_COLLECTION)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    dim = embedding_dim()
    LOGGER.info(
        "Re-index: provider=%s model=%s dim=%s collection=%s",
        embedding_provider(),
        embedding_model_name(),
        dim,
        args.collection,
    )

    chunks = fetch_chunks(args.limit, args.offset)
    if not chunks:
        LOGGER.warning("No chunks found in rag.document_chunk")
        return 1

    LOGGER.info("Loaded %s chunks (offset=%s)", len(chunks), args.offset)
    if args.dry_run:
        LOGGER.info("Dry run — no Qdrant writes")
        return 0

    client = get_qdrant_client()
    ensure_named_text_collection(client, args.collection)

    llm = LLMClient()
    written = 0
    batch: list[models.PointStruct] = []

    for row in chunks:
        text = row["chunk_text"]
        if len(text.strip()) < 8:
            continue
        vector = embed_text(text, llm=llm)
        meta = row["metadata"]
        corpus = meta.get("corpus") or "lab_operations"
        payload = {
            "chunk_uid": row["chunk_uid"],
            "document_code": row["document_code"],
            "title": row["title"],
            "section_id": meta.get("section_id"),
            "relative_path": meta.get("relative_path"),
            "section_path": row["section_path"],
            "corpus": corpus,
            "excerpt": text[:1200],
        }
        point_id = stable_point_uuid(row["chunk_uid"])
        batch.append(
            models.PointStruct(
                id=point_id,
                vector={TEXT_VECTOR_NAME: vector},
                payload=payload,
            )
        )
        if len(batch) >= args.batch_size:
            written += upsert_text_points(client, batch, collection=args.collection)
            batch.clear()
            LOGGER.info("Upserted %s points…", written)

    if batch:
        written += upsert_text_points(client, batch, collection=args.collection)

    LOGGER.info("Done — %s vectors upserted to %s", written, args.collection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
