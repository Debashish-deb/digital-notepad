"""OCR job queue — enqueue on needs_ocr and continue pipeline after worker OCR."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from app_skeleton.digitalization.models import ExtractedDocument, SourceFileManifest
from app_skeleton.digitalization.status import Status

LOGGER = logging.getLogger(__name__)

OCR_CONFIDENCE_THRESHOLD = 0.6


def _jsonb(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def ocr_engine_name() -> str:
    return (os.getenv("OCR_ENGINE", "tesseract") or "tesseract").strip().lower()


def enqueue_ocr_job(
    conn,
    *,
    manifest_id: str,
    extracted_document_id: str,
    source_path: str,
    root_path: str = "",
    asset_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """Insert platform.ocr_job when ENABLE_OCR=true. Returns job_id or None."""
    from app_skeleton.api.ocr.adapter import ocr_enabled

    if not ocr_enabled():
        return None

    job_meta = dict(metadata or {})
    if root_path:
        job_meta.setdefault("root_path", root_path)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO platform.ocr_job (
                manifest_id, extracted_document_id, document_id, asset_id,
                source_path, status, engine, metadata
            )
            SELECT %s, %s, %s, %s, %s, 'queued', %s, %s::jsonb
            WHERE NOT EXISTS (
                SELECT 1 FROM platform.ocr_job j
                WHERE j.manifest_id = %s
                  AND j.status IN ('queued', 'processing')
            )
            RETURNING job_id;
            """,
            (
                manifest_id,
                extracted_document_id,
                extracted_document_id,
                asset_id,
                source_path,
                ocr_engine_name(),
                _jsonb(job_meta),
                manifest_id,
            ),
        )
        row = cur.fetchone()
        if not row:
            return None
        return str(row[0])


def _load_manifest(conn, manifest_id: str) -> SourceFileManifest | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT provider, logical_path, file_name, file_ext, size_bytes,
                   modified_at, checksum_sha256, source_uri, status, metadata
            FROM platform.source_file_manifest
            WHERE id = %s;
            """,
            (manifest_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return SourceFileManifest(
        provider=row[0],
        logical_path=row[1],
        file_name=row[2],
        file_ext=row[3],
        size_bytes=row[4] or 0,
        modified_at=row[5].isoformat() if row[5] else None,
        checksum_sha256=row[6],
        source_uri=row[7],
        status=row[8],
        metadata=row[9] if isinstance(row[9], dict) else {},
        id=manifest_id,
    )


def _load_extracted(conn, extracted_document_id: str) -> ExtractedDocument | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT manifest_id, raw_text, raw_tables, raw_metadata, extractor_name,
                   extraction_status, extraction_confidence, warnings
            FROM platform.extracted_document
            WHERE id = %s;
            """,
            (extracted_document_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return ExtractedDocument(
        manifest_id=str(row[0]),
        raw_text=row[1] or "",
        raw_tables=row[2] if isinstance(row[2], list) else [],
        raw_metadata=row[3] if isinstance(row[3], dict) else {},
        extractor_name=row[4] or "unknown",
        extraction_status=row[5] or "not_attempted",
        extraction_confidence=float(row[6] or 0.0),
        warnings=row[7] if isinstance(row[7], list) else [],
        id=extracted_document_id,
    )


def continue_pipeline_after_ocr(
    conn,
    manifest: SourceFileManifest,
    extracted: ExtractedDocument,
    root: Path,
    *,
    ocr_confidence: float,
) -> dict[str, Any]:
    """Re-enter canonicalize → validate → chunk after OCR text is merged."""
    from app_skeleton.digitalization import canonicalizer, chunker, validators
    from app_skeleton.digitalization import registry_writer as rw

    low_confidence = ocr_confidence < OCR_CONFIDENCE_THRESHOLD
    extracted.raw_metadata = {
        **(extracted.raw_metadata or {}),
        "ocr_engine": ocr_engine_name(),
        "ocr_confidence": ocr_confidence,
    }

    if low_confidence:
        extracted.extraction_status = "needs_review"
        extracted.extraction_confidence = ocr_confidence
        extracted.warnings = list(extracted.warnings or []) + [
            f"OCR confidence {ocr_confidence:.2f} below threshold {OCR_CONFIDENCE_THRESHOLD}"
        ]
        rw.upsert_extracted(conn, extracted)
        rw.update_manifest_status(conn, manifest.id, Status.NEEDS_REVIEW)
        return {"pipeline": "review", "confidence": ocr_confidence}

    extracted.extraction_status = "extracted"
    extracted.extraction_confidence = ocr_confidence
    rw.upsert_extracted(conn, extracted)
    rw.update_manifest_status(conn, manifest.id, Status.EXTRACTED)

    rw.update_manifest_status(conn, manifest.id, Status.CANONICALIZING)
    canonical = canonicalizer.canonicalize(manifest, extracted)
    canonical.manifest_id = manifest.id
    canonical.extracted_document_id = extracted.id

    validation_status, validation_warnings = validators.validate_canonical(canonical)
    canonical.validation_status = validation_status
    canonical.warnings = validation_warnings

    if validation_status == "validation_failed":
        rw.update_manifest_status(conn, manifest.id, Status.VALIDATION_FAILED)
        canonical.needs_review = True
        rw.upsert_canonical(conn, canonical)
        return {"pipeline": "validation_failed", "confidence": ocr_confidence}

    rw.upsert_canonical(conn, canonical)
    rw.update_manifest_status(conn, manifest.id, Status.CANONICALIZED)

    chunks_inserted = 0
    if canonical.should_index:
        chunks = chunker.chunk_document(manifest, canonical)
        for chunk in chunks:
            chunk.canonical_document_id = canonical.id
        if chunks:
            chunks_inserted = rw.insert_chunks(conn, chunks)
            rw.update_manifest_status(conn, manifest.id, Status.CHUNKED)
            try:
                from app_skeleton.api.knowledge_indexer import index_digitalization_chunks
                from app_skeleton.api.platform_flags import knowledge_indexer_enabled

                if knowledge_indexer_enabled():
                    index_digitalization_chunks(
                        document_code=canonical.document_id or canonical.id or manifest.logical_path,
                        title=canonical.title or manifest.file_name,
                        source_type=canonical.document_type or "canonical_document",
                        chunks=chunks,
                        metadata={
                            "logical_path": manifest.logical_path,
                            "provider": manifest.provider,
                            "domain": canonical.domain,
                            "manifest_id": manifest.id,
                            "ocr_confidence": ocr_confidence,
                        },
                    )
            except Exception as exc:
                LOGGER.warning("knowledge_indexer hook failed after OCR for %s: %s", manifest.logical_path, exc)

    return {
        "pipeline": "completed",
        "confidence": ocr_confidence,
        "chunks_inserted": chunks_inserted,
    }


def apply_ocr_result(
    conn,
    *,
    job_id: str,
    manifest_id: str | None,
    extracted_document_id: str | None,
    source_path: str,
    metadata: dict[str, Any],
    result_text: str,
    confidence: float,
    engine: str,
    error: str | None = None,
) -> dict[str, Any]:
    """Persist OCR outcome and optionally continue the digitalization pipeline."""
    root_path = str(metadata.get("root_path") or "")
    root = Path(root_path).resolve() if root_path else Path(source_path).parent

    if error or not result_text.strip():
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE platform.ocr_job SET
                    status = 'failed',
                    error_message = %s,
                    confidence_score = %s,
                    result_text = %s,
                    finished_at = now()
                WHERE job_id = %s;
                """,
                (error or "empty OCR result", confidence, result_text, job_id),
            )
            if extracted_document_id:
                cur.execute(
                    """
                    UPDATE platform.extracted_document SET
                        extraction_status = 'ocr_failed',
                        extraction_confidence = %s,
                        raw_metadata = raw_metadata || %s::jsonb,
                        updated_at = now()
                    WHERE id = %s;
                    """,
                    (confidence, _jsonb({"ocr_error": error or "empty OCR result", "ocr_engine": engine}), extracted_document_id),
                )
        return {"job_status": "failed", "error": error or "empty OCR result"}

    pipeline_result: dict[str, Any] = {"job_status": "completed"}
    if confidence < OCR_CONFIDENCE_THRESHOLD:
        job_status = "review"
    else:
        job_status = "completed"

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE platform.ocr_job SET
                status = %s,
                confidence_score = %s,
                result_text = %s,
                error_message = NULL,
                finished_at = now()
            WHERE job_id = %s;
            """,
            (job_status, confidence, result_text, job_id),
        )

    if manifest_id and extracted_document_id:
        manifest = _load_manifest(conn, manifest_id)
        extracted = _load_extracted(conn, extracted_document_id)
        if manifest and extracted:
            extracted.raw_text = result_text
            pipeline_result = continue_pipeline_after_ocr(
                conn,
                manifest,
                extracted,
                root,
                ocr_confidence=confidence,
            )
            pipeline_result["job_status"] = job_status

    return pipeline_result
