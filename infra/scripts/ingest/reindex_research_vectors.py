#!/usr/bin/env python3
"""Re-embed platform.research_chunk rows into research_knowledge Qdrant collection.

Usage:
  python scripts/ingest/reindex_research_vectors.py --dry-run
  python scripts/ingest/reindex_research_vectors.py --limit 500
  EMBEDDING_PROVIDER=ollama TEXT_EMBEDDING_DIM=768 python scripts/ingest/reindex_research_vectors.py
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import psycopg

from omeia.api.embedding_service import embedding_dim, embedding_model_name, embedding_provider
from omeia.api.llm_client import LLMClient
from omeia.api.qdrant_collections import RESEARCH_KB
from omeia.api.qdrant_research_indexer import stable_point_id, upsert_research_chunks
from omeia.api.qdrant_vectors import ensure_named_text_collection, get_qdrant_client

LOGGER = logging.getLogger(__name__)


def _db_conn() -> str:
    from omeia.api.supabase_config import postgres_conn

    return postgres_conn()


def fetch_research_chunks(limit: int, offset: int) -> list[dict]:
    sql = """
        SELECT rc.chunk_id, rc.chunk_index, rc.text, rc.text_hash, rc.section_title, rc.token_count,
               rd.document_id, rd.title, rs.source_type, rs.canonical_url, rs.doi, rs.pmid,
               rs.dataset_accession, rd.visibility
        FROM platform.research_chunk rc
        JOIN platform.research_document rd ON rd.document_id = rc.document_id
        LEFT JOIN platform.research_source rs ON rs.source_id = rd.source_id
        ORDER BY rd.document_id, rc.chunk_index
        LIMIT %s OFFSET %s;
    """
    rows: list[dict] = []
    with psycopg.connect(_db_conn(), connect_timeout=12) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit, offset))
            for (
                chunk_id,
                chunk_index,
                text,
                text_hash,
                section_title,
                token_count,
                document_id,
                title,
                source_type,
                canonical_url,
                doi,
                pmid,
                dataset_accession,
                visibility,
            ) in cur.fetchall():
                rows.append({
                    "chunk_id": str(chunk_id),
                    "chunk_index": chunk_index,
                    "text": text or "",
                    "text_hash": text_hash,
                    "section_title": section_title,
                    "token_count": token_count,
                    "document_id": str(document_id),
                    "title": title,
                    "source_type": source_type,
                    "source_url": canonical_url,
                    "doi": doi,
                    "pmid": pmid,
                    "dataset_accession": dataset_accession,
                    "visibility": visibility or "public",
                })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--collection", default=RESEARCH_KB)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    dim = embedding_dim()
    LOGGER.info(
        "Research re-index: provider=%s model=%s dim=%s collection=%s",
        embedding_provider(),
        embedding_model_name(),
        dim,
        args.collection,
    )

    chunks = fetch_research_chunks(args.limit, args.offset)
    if not chunks:
        LOGGER.warning("No rows found in platform.research_chunk")
        return 1

    LOGGER.info("Loaded %s research chunks (offset=%s)", len(chunks), args.offset)
    if args.dry_run:
        LOGGER.info("Dry run — no Qdrant writes")
        return 0

    client = get_qdrant_client()
    ensure_named_text_collection(client, args.collection)

    llm = LLMClient()
    by_doc: dict[str, list[dict]] = {}
    doc_meta: dict[str, dict] = {}
    for row in chunks:
        doc_id = row["document_id"]
        by_doc.setdefault(doc_id, []).append({
            "chunk_index": row["chunk_index"],
            "text": row["text"],
            "text_hash": row["text_hash"],
            "section_title": row["section_title"],
            "token_count": row["token_count"],
            "chunk_id": row["chunk_id"],
        })
        doc_meta.setdefault(doc_id, {
            "document_id": doc_id,
            "title": row["title"],
            "source_type": row["source_type"],
            "source_url": row["source_url"],
            "doi": row["doi"],
            "pmid": row["pmid"],
            "dataset_accession": row["dataset_accession"],
            "visibility": row["visibility"],
        })

    total = 0
    for doc_id, doc_chunks in by_doc.items():
        result = upsert_research_chunks(client, llm, doc_chunks, doc_meta[doc_id])
        total += result.get("points_indexed", 0)
        LOGGER.info("Document %s: %s points", doc_id, result.get("points_indexed", 0))

    LOGGER.info("Done — %s vectors upserted to %s", total, args.collection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
