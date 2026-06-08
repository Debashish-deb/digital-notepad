"""Research knowledge base persistence: Postgres platform.* + Qdrant research_knowledge."""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb
from qdrant_client import QdrantClient

from app_skeleton.api.dataset_fetcher import normalize_dataset_record, seed_dataset_registry
from app_skeleton.api.entity_relation_extractor import (
    extract_entities_rule_based,
    extract_relations_rule_based,
    normalize_name,
)
from app_skeleton.api.qdrant_research_indexer import (
    COLLECTION,
    VECTOR_NAME,
    ensure_research_collection,
    search_research_knowledge as qdrant_search,
    stable_point_id,
    upsert_research_chunks,
)
from app_skeleton.api.research_crawler import CrawledPage
from app_skeleton.api.research_knowledge_models import ResearchKnowledgeStatus
from app_skeleton.api.research_search_service import (
    normalize_research_hit,
    tokenize_query,
)
from app_skeleton.api.scientific_document_parser import chunk_document, clean_scientific_text

LOGGER = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs" / "research_knowledge"


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


def _load_seed_urls() -> list[str]:
    seed_path = CONFIG_DIR / "seed_sources.json"
    if not seed_path.is_file():
        return [
            "https://www.farkkilab.org/",
            "https://www.farkkilab.org/research",
            "https://www.farkkilab.org/publications",
            "https://www.farkkilab.org/clinic",
            "https://www.farkkilab.org/news",
        ]
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    urls: list[str] = []
    for block_key in ("lab_public_sources", "publication_seeds", "dataset_seeds"):
        for item in data.get(block_key) or []:
            url = (item.get("url") or "").strip()
            if url:
                urls.append(url)
    return urls or [
        "https://www.farkkilab.org/",
        "https://www.farkkilab.org/research",
        "https://www.farkkilab.org/publications",
    ]


def _schema_ok(cur) -> bool:
    cur.execute("SELECT to_regclass('platform.research_source');")
    return bool(cur.fetchone()[0])


def _table_counts(cur) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in (
        "research_source",
        "research_document",
        "research_chunk",
        "research_dataset",
        "knowledge_entity",
        "knowledge_relation",
    ):
        try:
            cur.execute(f"SELECT COUNT(*) FROM platform.{table};")
            counts[table] = int(cur.fetchone()[0])
        except Exception:
            counts[table] = 0
    return counts


def get_status(*, qdrant: QdrantClient | None = None) -> ResearchKnowledgeStatus:
    warnings: list[str] = []
    schema_ok = False
    counts = {
        "source_count": 0,
        "document_count": 0,
        "chunk_count": 0,
        "dataset_count": 0,
        "entity_count": 0,
        "relation_count": 0,
    }
    qdrant_connected = False
    points_count = 0

    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                schema_ok = _schema_ok(cur)
                if schema_ok:
                    raw = _table_counts(cur)
                    counts = {
                        "source_count": raw.get("research_source", 0),
                        "document_count": raw.get("research_document", 0),
                        "chunk_count": raw.get("research_chunk", 0),
                        "dataset_count": raw.get("research_dataset", 0),
                        "entity_count": raw.get("knowledge_entity", 0),
                        "relation_count": raw.get("knowledge_relation", 0),
                    }
    except Exception as exc:
        warnings.append(f"Postgres unavailable: {exc}")

    if qdrant is not None:
        try:
            ensure_research_collection(qdrant)
            info = qdrant.get_collection(COLLECTION)
            qdrant_connected = True
            points_count = int(getattr(info, "points_count", 0) or 0)
        except Exception as exc:
            warnings.append(f"Qdrant unavailable: {exc}")
    else:
        warnings.append("Qdrant client not configured.")

    if not schema_ok:
        warnings.append("Apply sql/142_research_knowledge.sql to enable research tables.")

    return ResearchKnowledgeStatus(
        qdrant_connected=qdrant_connected,
        collection=COLLECTION,
        vector_name=VECTOR_NAME,
        schema_ok=schema_ok,
        points_count=points_count,
        warnings=warnings,
        **counts,
    )


def _upsert_source(
    cur,
    *,
    source_type: str,
    title: str,
    url: str | None = None,
    canonical_url: str | None = None,
    doi: str | None = None,
    pmid: str | None = None,
    dataset_accession: str | None = None,
    journal: str | None = None,
    publication_year: int | None = None,
    authors: list[Any] | None = None,
    abstract: str | None = None,
    checksum: str | None = None,
    status: str = "fetched",
    metadata: dict[str, Any] | None = None,
) -> uuid.UUID:
    cur.execute(
        """
        INSERT INTO platform.research_source (
            source_type, title, url, canonical_url, doi, pmid, dataset_accession,
            journal, publication_year, authors, abstract, checksum, status,
            fetched_at, last_checked_at, metadata
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now(), %s
        )
        ON CONFLICT (canonical_url) WHERE canonical_url IS NOT NULL DO UPDATE SET
            title = EXCLUDED.title,
            url = EXCLUDED.url,
            doi = COALESCE(EXCLUDED.doi, platform.research_source.doi),
            pmid = COALESCE(EXCLUDED.pmid, platform.research_source.pmid),
            journal = COALESCE(EXCLUDED.journal, platform.research_source.journal),
            publication_year = COALESCE(EXCLUDED.publication_year, platform.research_source.publication_year),
            authors = EXCLUDED.authors,
            abstract = COALESCE(EXCLUDED.abstract, platform.research_source.abstract),
            checksum = EXCLUDED.checksum,
            status = EXCLUDED.status,
            last_checked_at = now(),
            metadata = platform.research_source.metadata || EXCLUDED.metadata,
            updated_at = now()
        RETURNING source_id;
        """,
        (
            source_type,
            title,
            url,
            canonical_url,
            doi,
            pmid,
            dataset_accession,
            journal,
            publication_year,
            Jsonb(authors or []),
            abstract,
            checksum,
            status,
            Jsonb(metadata or {}),
        ),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    # Fallback lookup when canonical_url is null (datasets/publications by accession/doi)
    if doi:
        cur.execute("SELECT source_id FROM platform.research_source WHERE doi = %s LIMIT 1;", (doi,))
    elif pmid:
        cur.execute("SELECT source_id FROM platform.research_source WHERE pmid = %s LIMIT 1;", (pmid,))
    elif dataset_accession:
        cur.execute(
            "SELECT source_id FROM platform.research_source WHERE dataset_accession = %s LIMIT 1;",
            (dataset_accession,),
        )
    else:
        cur.execute(
            "SELECT source_id FROM platform.research_source WHERE url = %s ORDER BY updated_at DESC LIMIT 1;",
            (url,),
        )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Failed to upsert research source: {title}")
    return row[0]


def _upsert_document(
    cur,
    *,
    source_id: uuid.UUID,
    title: str,
    document_type: str,
    raw_text: str,
    clean_text: str,
    metadata: dict[str, Any] | None = None,
) -> uuid.UUID:
    cur.execute(
        """
        SELECT document_id FROM platform.research_document
        WHERE source_id = %s AND title = %s
        ORDER BY updated_at DESC LIMIT 1;
        """,
        (source_id, title),
    )
    row = cur.fetchone()
    if row:
        document_id = row[0]
        cur.execute(
            """
            UPDATE platform.research_document
            SET raw_text = %s, clean_text = %s, document_type = %s,
                metadata = metadata || %s, updated_at = now()
            WHERE document_id = %s;
            """,
            (raw_text, clean_text, document_type, Jsonb(metadata or {}), document_id),
        )
        return document_id
    cur.execute(
        """
        INSERT INTO platform.research_document (
            source_id, title, document_type, raw_text, clean_text, metadata
        ) VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING document_id;
        """,
        (source_id, title, document_type, raw_text, clean_text, Jsonb(metadata or {})),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Failed to upsert research document: {title}")
    return row[0]


def _replace_chunks(cur, document_id: uuid.UUID, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cur.execute("DELETE FROM platform.research_chunk WHERE document_id = %s;", (document_id,))
    stored: list[dict[str, Any]] = []
    for chunk in chunks:
        cur.execute(
            """
            INSERT INTO platform.research_chunk (
                document_id, chunk_index, text, text_hash, token_count,
                section_title, qdrant_collection, vector_status, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)
            RETURNING chunk_id;
            """,
            (
                document_id,
                chunk["chunk_index"],
                chunk["text"],
                chunk["text_hash"],
                chunk.get("token_count"),
                chunk.get("section_title"),
                COLLECTION,
                Jsonb({}),
            ),
        )
        chunk_id = cur.fetchone()[0]
        stored.append({**chunk, "chunk_id": str(chunk_id)})
    return stored


def _upsert_entity(cur, entity: dict[str, Any], source_id: uuid.UUID) -> uuid.UUID:
    cur.execute(
        """
        INSERT INTO platform.knowledge_entity (
            name, normalized_name, entity_type, aliases, confidence, source_ids
        ) VALUES (%s, %s, %s, %s, %s, ARRAY[%s]::uuid[])
        ON CONFLICT (normalized_name, entity_type) DO UPDATE SET
            aliases = (
                SELECT ARRAY(SELECT DISTINCT unnest(
                    platform.knowledge_entity.aliases || EXCLUDED.aliases
                ))
            ),
            source_ids = (
                SELECT ARRAY(SELECT DISTINCT unnest(
                    platform.knowledge_entity.source_ids || EXCLUDED.source_ids
                ))
            ),
            confidence = GREATEST(platform.knowledge_entity.confidence, EXCLUDED.confidence),
            updated_at = now()
        RETURNING entity_id;
        """,
        (
            entity["name"],
            entity["normalized_name"],
            entity["entity_type"],
            entity.get("aliases") or [],
            entity.get("confidence", 0.0),
            source_id,
        ),
    )
    return cur.fetchone()[0]


def _upsert_relation(
    cur,
    *,
    subject_id: uuid.UUID,
    object_name: str,
    relation_type: str,
    evidence_text: str | None,
    source_id: uuid.UUID,
    confidence: float,
) -> None:
    object_norm = normalize_name(object_name)
    cur.execute(
        """
        INSERT INTO platform.knowledge_entity (name, normalized_name, entity_type)
        VALUES (%s, %s, 'concept')
        ON CONFLICT (normalized_name, entity_type) DO UPDATE SET updated_at = now()
        RETURNING entity_id;
        """,
        (object_name, object_norm),
    )
    object_id = cur.fetchone()[0]
    cur.execute(
        """
        SELECT relation_id FROM platform.knowledge_relation
        WHERE subject_entity_id = %s AND object_entity_id = %s
          AND relation_type = %s AND source_id = %s
        LIMIT 1;
        """,
        (subject_id, object_id, relation_type, source_id),
    )
    if cur.fetchone():
        return
    cur.execute(
        """
        INSERT INTO platform.knowledge_relation (
            subject_entity_id, relation_type, object_entity_id,
            evidence_text, source_id, confidence
        ) VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (subject_id, relation_type, object_id, evidence_text, source_id, confidence),
    )


def _index_document(
    cur,
    *,
    document_id: uuid.UUID,
    source_id: uuid.UUID,
    title: str,
    source_type: str,
    source_url: str | None,
    doi: str | None,
    pmid: str | None,
    dataset_accession: str | None,
    entity_names: list[str],
    chunks: list[dict[str, Any]],
    qdrant: QdrantClient | None,
    llm: Any,
) -> int:
    if not chunks:
        return 0
    indexed = 0
    base_payload = {
        "document_id": str(document_id),
        "source_id": str(source_id),
        "title": title,
        "source_type": source_type,
        "source_url": source_url,
        "doi": doi,
        "pmid": pmid,
        "dataset_accession": dataset_accession,
        "visibility": "public",
        "entities": entity_names,
        "bucket": "research",
    }
    if qdrant is not None and llm is not None:
        try:
            result = upsert_research_chunks(qdrant, llm, chunks, base_payload)
            indexed = int(result.get("points_indexed") or 0)
            for chunk in chunks:
                point_id = stable_point_id(str(document_id), str(chunk["chunk_index"]), chunk.get("text_hash"))
                cur.execute(
                    """
                    UPDATE platform.research_chunk
                    SET qdrant_point_id = %s, vector_status = 'indexed', qdrant_collection = %s
                    WHERE document_id = %s AND chunk_index = %s;
                    """,
                    (point_id, COLLECTION, document_id, chunk["chunk_index"]),
                )
        except Exception as exc:
            LOGGER.warning("Qdrant indexing failed for %s: %s", title, exc)
            cur.execute(
                "UPDATE platform.research_chunk SET vector_status = 'failed' WHERE document_id = %s;",
                (document_id,),
            )
    cur.execute(
        "UPDATE platform.research_source SET status = 'indexed', updated_at = now() WHERE source_id = %s;",
        (source_id,),
    )
    return indexed


def ingest_web_page(
    page: CrawledPage,
    *,
    qdrant: QdrantClient | None = None,
    llm: Any = None,
) -> dict[str, Any]:
    clean = clean_scientific_text(page.text)
    chunks = chunk_document(clean)
    entities = extract_entities_rule_based(clean)
    entity_names = [e["name"] for e in entities]

    with psycopg.connect(_db_conn(), connect_timeout=15) as conn:
        with conn.cursor() as cur:
            source_id = _upsert_source(
                cur,
                source_type="website",
                title=page.title or page.canonical_url,
                url=page.url,
                canonical_url=page.canonical_url,
                checksum=page.checksum,
                status="parsed",
                metadata={"status_code": page.status_code},
            )
            document_id = _upsert_document(
                cur,
                source_id=source_id,
                title=page.title or page.canonical_url,
                document_type="web_page",
                raw_text=page.text,
                clean_text=clean,
            )
            stored_chunks = _replace_chunks(cur, document_id, chunks)
            name_to_id: dict[str, uuid.UUID] = {}
            for ent in entities:
                name_to_id[ent["name"]] = _upsert_entity(cur, ent, source_id)
            relations = extract_relations_rule_based(clean, entities, source_id=str(source_id))
            for rel in relations:
                subj = name_to_id.get(rel["subject"])
                if subj:
                    _upsert_relation(
                        cur,
                        subject_id=subj,
                        object_name=rel["object"],
                        relation_type=rel["relation_type"],
                        evidence_text=rel.get("evidence_text"),
                        source_id=source_id,
                        confidence=float(rel.get("confidence") or 0.0),
                    )
            indexed = _index_document(
                cur,
                document_id=document_id,
                source_id=source_id,
                title=page.title or page.canonical_url,
                source_type="website",
                source_url=page.canonical_url,
                doi=None,
                pmid=None,
                dataset_accession=None,
                entity_names=entity_names,
                chunks=stored_chunks,
                qdrant=qdrant,
                llm=llm,
            )
        conn.commit()

    return {
        "source_id": str(source_id),
        "document_id": str(document_id),
        "chunks": len(stored_chunks),
        "indexed": indexed,
        "entities": len(entities),
    }


def ingest_crawled_pages(
    pages: list[CrawledPage],
    *,
    qdrant: QdrantClient | None = None,
    llm: Any = None,
) -> dict[str, Any]:
    results = []
    for page in pages:
        try:
            results.append(ingest_web_page(page, qdrant=qdrant, llm=llm))
        except Exception as exc:
            LOGGER.warning("Failed to ingest %s: %s", page.canonical_url, exc)
            results.append({"url": page.canonical_url, "error": str(exc)})
    return {
        "page_count": len(pages),
        "ingested": sum(1 for r in results if "error" not in r),
        "results": results[:20],
    }


def _publication_index_text(record: dict[str, Any], *, title: str, abstract: str) -> str:
    parts: list[str] = [title]
    authors = record.get("authors") or []
    author_names: list[str] = []
    for author in authors[:16]:
        if isinstance(author, dict):
            name = (author.get("name") or "").strip()
            if not name:
                given = (author.get("given") or author.get("Given") or "").strip()
                family = (author.get("family") or author.get("Last") or "").strip()
                name = f"{given} {family}".strip()
            if name:
                author_names.append(name)
        elif author:
            author_names.append(str(author).strip())
    if author_names:
        parts.append("Authors: " + "; ".join(author_names))
    journal = (record.get("journal") or "").strip()
    if journal:
        parts.append(f"Journal: {journal}")
    year = record.get("publication_year")
    if year:
        parts.append(f"Year: {year}")
    if abstract:
        parts.append(abstract)
    return "\n\n".join(part for part in parts if part)


def ingest_publication_record(
    record: dict[str, Any],
    *,
    qdrant: QdrantClient | None = None,
    llm: Any = None,
) -> dict[str, Any]:
    title = (record.get("title") or "Untitled publication").strip()
    abstract = (record.get("abstract") or "").strip()
    text = _publication_index_text(record, title=title, abstract=abstract)
    clean = clean_scientific_text(text)
    chunks = chunk_document(clean) if clean else []
    entities = extract_entities_rule_based(clean)
    doi = record.get("doi")
    pmid = record.get("pmid")
    url = record.get("url") or (f"https://doi.org/{doi}" if doi else None)

    with psycopg.connect(_db_conn(), connect_timeout=15) as conn:
        with conn.cursor() as cur:
            source_id = _upsert_source(
                cur,
                source_type="publication_metadata",
                title=title,
                url=url,
                canonical_url=url,
                doi=doi,
                pmid=str(pmid) if pmid else None,
                journal=record.get("journal"),
                publication_year=record.get("publication_year"),
                authors=record.get("authors") or [],
                abstract=abstract or None,
                status="parsed",
                metadata={"discovery_query": record.get("discovery_query")},
            )
            document_id = _upsert_document(
                cur,
                source_id=source_id,
                title=title,
                document_type="publication_metadata",
                raw_text=text,
                clean_text=clean,
                metadata={"journal": record.get("journal")},
            )
            stored_chunks = _replace_chunks(cur, document_id, chunks)
            for ent in entities:
                _upsert_entity(cur, ent, source_id)
            indexed = _index_document(
                cur,
                document_id=document_id,
                source_id=source_id,
                title=title,
                source_type="publication_metadata",
                source_url=url,
                doi=doi,
                pmid=str(pmid) if pmid else None,
                dataset_accession=None,
                entity_names=[e["name"] for e in entities],
                chunks=stored_chunks,
                qdrant=qdrant,
                llm=llm,
            )
        conn.commit()

    return {"source_id": str(source_id), "title": title, "chunks": len(stored_chunks), "indexed": indexed}


def ingest_publications(
    records: list[dict[str, Any]],
    *,
    qdrant: QdrantClient | None = None,
    llm: Any = None,
) -> dict[str, Any]:
    results = []
    for rec in records:
        try:
            results.append(ingest_publication_record(rec, qdrant=qdrant, llm=llm))
        except Exception as exc:
            LOGGER.warning("Publication ingest failed for %s: %s", rec.get("title"), exc)
            results.append({"title": rec.get("title"), "error": str(exc)})
    return {
        "count": len(records),
        "ingested": sum(1 for r in results if "error" not in r),
        "records": results[:20],
    }


def seed_datasets(*, qdrant: QdrantClient | None = None, llm: Any = None) -> dict[str, Any]:
    records = [normalize_dataset_record(r) for r in seed_dataset_registry()]
    seeded = []
    with psycopg.connect(_db_conn(), connect_timeout=15) as conn:
        with conn.cursor() as cur:
            for rec in records:
                cur.execute(
                    """
                    INSERT INTO platform.research_dataset (
                        accession, source_database, title, disease, modality, organism,
                        technology, url, access_level, usable_for, limitations, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_database, accession) WHERE accession IS NOT NULL DO UPDATE SET
                        title = EXCLUDED.title,
                        disease = EXCLUDED.disease,
                        modality = EXCLUDED.modality,
                        technology = EXCLUDED.technology,
                        url = EXCLUDED.url,
                        usable_for = EXCLUDED.usable_for,
                        limitations = EXCLUDED.limitations,
                        metadata = platform.research_dataset.metadata || EXCLUDED.metadata,
                        updated_at = now()
                    RETURNING dataset_id;
                    """,
                    (
                        rec.get("accession"),
                        rec["source_database"],
                        rec["title"],
                        rec.get("disease"),
                        rec.get("modality") or [],
                        rec.get("organism", "Homo sapiens"),
                        rec.get("technology") or [],
                        rec.get("url"),
                        "public",
                        rec.get("usable_for") or [],
                        rec.get("limitations") or [],
                        Jsonb(rec),
                    ),
                )
                dataset_id = cur.fetchone()[0]
                blurb = " ".join(
                    filter(
                        None,
                        [
                            rec.get("title"),
                            rec.get("disease"),
                            " ".join(rec.get("modality") or []),
                            " ".join(rec.get("technology") or []),
                            rec.get("url"),
                        ],
                    )
                )
                source_id = _upsert_source(
                    cur,
                    source_type="dataset",
                    title=rec["title"],
                    url=rec.get("url"),
                    canonical_url=rec.get("url"),
                    dataset_accession=rec.get("accession"),
                    abstract=blurb[:2000],
                    status="indexed",
                    metadata={"source_database": rec["source_database"]},
                )
                cur.execute(
                    "UPDATE platform.research_dataset SET related_source_id = %s WHERE dataset_id = %s;",
                    (source_id, dataset_id),
                )
                clean = clean_scientific_text(blurb)
                chunks = chunk_document(clean)
                document_id = _upsert_document(
                    cur,
                    source_id=source_id,
                    title=rec["title"],
                    document_type="dataset_registry",
                    raw_text=blurb,
                    clean_text=clean,
                    metadata={"accession": rec.get("accession")},
                )
                stored_chunks = _replace_chunks(cur, document_id, chunks)
                indexed = _index_document(
                    cur,
                    document_id=document_id,
                    source_id=source_id,
                    title=rec["title"],
                    source_type="dataset",
                    source_url=rec.get("url"),
                    doi=None,
                    pmid=None,
                    dataset_accession=rec.get("accession"),
                    entity_names=[],
                    chunks=stored_chunks,
                    qdrant=qdrant,
                    llm=llm,
                )
                seeded.append(
                    {
                        "dataset_id": str(dataset_id),
                        "accession": rec.get("accession"),
                        "indexed": indexed,
                    }
                )
        conn.commit()
    return {"count": len(seeded), "datasets": seeded}


def _postgres_keyword_search(query: str, *, limit: int) -> list[dict[str, Any]]:
    pattern = f"%{query}%"
    hits: list[dict[str, Any]] = []
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                if not _schema_ok(cur):
                    return []
                cur.execute(
                    """
                    SELECT source_id::text, title, source_type, url, doi, pmid,
                           dataset_accession, COALESCE(abstract, '')
                    FROM platform.research_source
                    WHERE title ILIKE %s OR abstract ILIKE %s
                    ORDER BY updated_at DESC
                    LIMIT %s;
                    """,
                    (pattern, pattern, limit),
                )
                for row in cur.fetchall():
                    hits.append({
                        "id": row[0],
                        "source_id": row[0],
                        "title": row[1],
                        "source_type": row[2],
                        "source_url": row[3],
                        "doi": row[4],
                        "pmid": row[5],
                        "dataset_accession": row[6],
                        "snippet": (row[7] or "")[:900],
                        "score": 0.55,
                    })
                cur.execute(
                    """
                    SELECT d.document_id::text, d.title, s.source_type, s.url, s.doi, s.pmid,
                           s.dataset_accession, LEFT(COALESCE(d.clean_text, d.raw_text, ''), 900)
                    FROM platform.research_document d
                    JOIN platform.research_source s ON d.source_id = s.source_id
                    WHERE d.title ILIKE %s OR d.clean_text ILIKE %s
                    ORDER BY d.updated_at DESC
                    LIMIT %s;
                    """,
                    (pattern, pattern, limit),
                )
                for row in cur.fetchall():
                    hits.append({
                        "id": row[0],
                        "title": row[1],
                        "source_type": row[2],
                        "source_url": row[3],
                        "doi": row[4],
                        "pmid": row[5],
                        "dataset_accession": row[6],
                        "snippet": row[7] or "",
                        "score": 0.5,
                    })
                cur.execute(
                    """
                    SELECT dataset_id::text, title, 'dataset', url, NULL, NULL, accession,
                           LEFT(title || ' ' || COALESCE(disease, '') || ' ' || array_to_string(modality, ' '), 900)
                    FROM platform.research_dataset
                    WHERE title ILIKE %s OR disease ILIKE %s OR accession ILIKE %s
                    ORDER BY updated_at DESC
                    LIMIT %s;
                    """,
                    (pattern, pattern, pattern, limit),
                )
                for row in cur.fetchall():
                    hits.append({
                        "id": row[0],
                        "title": row[1],
                        "source_type": "dataset",
                        "source_url": row[3],
                        "doi": None,
                        "pmid": None,
                        "dataset_accession": row[6],
                        "snippet": row[7] or "",
                        "score": 0.48,
                    })
    except Exception as exc:
        LOGGER.warning("Research Postgres search failed: %s", exc)
    return hits


def search_research(
    query: str,
    *,
    limit: int = 20,
    qdrant: QdrantClient | None = None,
    llm: Any = None,
) -> dict[str, Any]:
    terms = tokenize_query(query)
    merged: dict[str, dict[str, Any]] = {}

    for raw in _postgres_keyword_search(query, limit=limit):
        hit = normalize_research_hit(raw, terms)
        merged[hit["id"]] = hit

    if qdrant is not None and llm is not None:
        try:
            for raw in qdrant_search(qdrant, llm, query, limit=limit):
                hit = normalize_research_hit(raw, terms)
                existing = merged.get(hit["id"])
                if existing:
                    hit["score"] = max(existing["score"], hit["score"])
                merged[hit["id"]] = hit
        except Exception as exc:
            LOGGER.warning("Research Qdrant search failed: %s", exc)

    hits = sorted(merged.values(), key=lambda h: h.get("score", 0), reverse=True)[:limit]
    warnings: list[str] = []
    if qdrant is None:
        warnings.append("Qdrant client not configured — semantic research search is unavailable.")
    elif not hits:
        warnings.append("No research knowledge matches found. Run crawl/ingest in Research KB admin or check index status.")
    return {"query": query, "count": len(hits), "hits": hits, "warnings": warnings, "warning": warnings[0] if warnings else None}


def crawl_farkkila_seeds(
    *,
    max_pages: int = 20,
    qdrant: QdrantClient | None = None,
    llm: Any = None,
) -> dict[str, Any]:
    from app_skeleton.api.research_crawler import crawl_seed_urls

    delay = float(os.getenv("RESEARCH_KB_CRAWL_DELAY_SECONDS", "1.0"))
    pages = crawl_seed_urls(_load_seed_urls(), max_pages=max_pages, delay_seconds=delay)
    ingest_result = ingest_crawled_pages(pages, qdrant=qdrant, llm=llm)
    return {
        "status": "completed",
        "page_count": len(pages),
        "ingest": ingest_result,
        "pages": [
            {"url": p.canonical_url, "title": p.title, "chars": len(p.text)}
            for p in pages[:10]
        ],
    }
