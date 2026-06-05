"""Registry writer — persist digitalization records to Postgres."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import psycopg

from app_skeleton.digitalization.models import (
    CanonicalDocument,
    DocumentChunk,
    ExtractedDocument,
    SourceFileManifest,
)

LOGGER = logging.getLogger(__name__)


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn
    return postgres_conn()


def _scrub_null(val: Any) -> Any:
    if isinstance(val, str):
        return val.replace("\x00", "")
    if isinstance(val, dict):
        return {k: _scrub_null(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_scrub_null(v) for v in val]
    return val


def _jsonb(obj: Any) -> str:
    return json.dumps(_scrub_null(obj), ensure_ascii=False)


def upsert_manifest(conn, manifest: SourceFileManifest) -> str:
    """Upsert a source_file_manifest row. Returns the row ID."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO platform.source_file_manifest (
                provider, logical_path, source_uri, file_name, file_ext,
                size_bytes, modified_at, checksum_sha256, status, metadata,
                discovered_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s::timestamptz, %s, %s, %s::jsonb,
                now(), now()
            )
            ON CONFLICT (provider, logical_path, checksum_sha256) DO UPDATE SET
                size_bytes = EXCLUDED.size_bytes,
                modified_at = EXCLUDED.modified_at,
                status = EXCLUDED.status,
                metadata = EXCLUDED.metadata,
                updated_at = now()
            RETURNING id;
            """,
            (
                manifest.provider,
                manifest.logical_path,
                manifest.source_uri,
                manifest.file_name,
                manifest.file_ext,
                manifest.size_bytes,
                manifest.modified_at,
                manifest.checksum_sha256 or "",
                manifest.status,
                _jsonb(manifest.metadata),
            ),
        )
        row = cur.fetchone()
        manifest.id = str(row[0])
        return manifest.id


def upsert_extracted(conn, extracted: ExtractedDocument) -> str:
    """Upsert extracted_document. Returns row ID."""
    with conn.cursor() as cur:
        # Check if one already exists for this manifest
        cur.execute(
            "SELECT id FROM platform.extracted_document WHERE manifest_id = %s ORDER BY created_at DESC LIMIT 1;",
            (extracted.manifest_id,),
        )
        existing = cur.fetchone()

        if existing:
            doc_id = str(existing[0])
            cur.execute(
                """
                UPDATE platform.extracted_document SET
                    raw_text = %s,
                    raw_tables = %s::jsonb,
                    raw_metadata = %s::jsonb,
                    extractor_name = %s,
                    extraction_status = %s,
                    extraction_confidence = %s,
                    warnings = %s::jsonb,
                    updated_at = now()
                WHERE id = %s;
                """,
                (
                    _scrub_null(extracted.raw_text),
                    _jsonb(extracted.raw_tables),
                    _jsonb(extracted.raw_metadata),
                    extracted.extractor_name,
                    extracted.extraction_status,
                    extracted.extraction_confidence,
                    _jsonb(extracted.warnings),
                    doc_id,
                ),
            )
        else:
            doc_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO platform.extracted_document (
                    id, manifest_id, raw_text, raw_tables, raw_metadata,
                    extractor_name, extraction_status, extraction_confidence,
                    warnings
                ) VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s::jsonb);
                """,
                (
                    doc_id,
                    extracted.manifest_id,
                    _scrub_null(extracted.raw_text),
                    _jsonb(extracted.raw_tables),
                    _jsonb(extracted.raw_metadata),
                    extracted.extractor_name,
                    extracted.extraction_status,
                    extracted.extraction_confidence,
                    _jsonb(extracted.warnings),
                ),
            )

        extracted.id = doc_id
        return doc_id


def upsert_canonical(conn, canonical: CanonicalDocument) -> str:
    """Upsert canonical_document. Returns row ID."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO platform.canonical_document (
                manifest_id, extracted_document_id, document_id,
                title, document_type, domain,
                language_original, language_canonical,
                canonical_json, canonical_text, short_summary,
                should_index, needs_review, validation_status, warnings
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s::jsonb, %s, %s,
                %s, %s, %s, %s::jsonb
            )
            ON CONFLICT (document_id) DO UPDATE SET
                title = EXCLUDED.title,
                document_type = EXCLUDED.document_type,
                domain = EXCLUDED.domain,
                canonical_json = EXCLUDED.canonical_json,
                canonical_text = EXCLUDED.canonical_text,
                short_summary = EXCLUDED.short_summary,
                should_index = EXCLUDED.should_index,
                needs_review = EXCLUDED.needs_review,
                validation_status = EXCLUDED.validation_status,
                warnings = EXCLUDED.warnings,
                updated_at = now()
            RETURNING id;
            """,
            (
                canonical.manifest_id,
                canonical.extracted_document_id,
                canonical.document_id,
                canonical.title,
                canonical.document_type,
                canonical.domain,
                canonical.language_original,
                canonical.language_canonical,
                _jsonb(canonical.canonical_json),
                _scrub_null(canonical.canonical_text),
                canonical.short_summary[:500] if canonical.short_summary else "",
                canonical.should_index,
                canonical.needs_review,
                canonical.validation_status,
                _jsonb(canonical.warnings),
            ),
        )
        row = cur.fetchone()
        canonical.id = str(row[0])
        return canonical.id


def insert_chunks(conn, chunks: list[DocumentChunk]) -> int:
    """Insert document chunks. Skips existing chunk_ids. Returns count inserted."""
    if not chunks:
        return 0

    inserted = 0
    with conn.cursor() as cur:
        for chunk in chunks:
            try:
                cur.execute(
                    """
                    INSERT INTO platform.document_chunk (
                        canonical_document_id, chunk_id, chunk_index,
                        text, metadata, token_count, embedding_status
                    ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                    ON CONFLICT (chunk_id) DO NOTHING;
                    """,
                    (
                        chunk.canonical_document_id,
                        chunk.chunk_id,
                        chunk.chunk_index,
                        _scrub_null(chunk.text),
                        _jsonb(chunk.metadata),
                        chunk.token_count,
                        chunk.embedding_status,
                    ),
                )
                inserted += cur.rowcount
            except Exception as exc:
                LOGGER.warning("Chunk insert failed for %s: %s", chunk.chunk_id, exc)

    return inserted


def log_event(
    conn,
    *,
    event_type: str,
    status: str = "",
    message: str = "",
    job_id: str | None = None,
    manifest_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Write to digitalization_event_log."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO platform.digitalization_event_log (
                job_id, manifest_id, event_type, status, message, details
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb);
            """,
            (
                job_id,
                manifest_id,
                event_type,
                status,
                message[:2000],
                _jsonb(details or {}),
            ),
        )


def update_manifest_status(conn, manifest_id: str, status: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE platform.source_file_manifest SET status = %s, updated_at = now() WHERE id = %s;",
            (status, manifest_id),
        )
