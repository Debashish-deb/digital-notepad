"""Ingestion job orchestrator — scan → extract → canonicalize → validate → register → chunk."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg

from app_skeleton.digitalization import (
    canonicalizer,
    chunker,
    extractors,
    manifest as manifest_mod,
    registry_writer as rw,
    validators,
)
from app_skeleton.digitalization.models import DigitalizationJob, SourceFileManifest
from app_skeleton.digitalization.status import JobStatus, Status

LOGGER = logging.getLogger(__name__)


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn
    return postgres_conn()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_digitalization(
    *,
    provider: str = "local",
    root_path: str = "",
    dry_run: bool = False,
    max_files: int | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    """Run the full digitalization pipeline."""
    root = Path(root_path).resolve() if root_path else None
    if root and not root.is_dir():
        return {"error": f"Root path not found: {root_path}", "status": "failed"}

    job = DigitalizationJob(
        provider=provider,
        root_path=root_path,
        status=JobStatus.RUNNING,
        started_at=_utc_now(),
        dry_run=dry_run,
        created_by=created_by,
    )

    counts: dict[str, int] = {
        "discovered": 0,
        "extracted": 0,
        "extraction_failed": 0,
        "canonicalized": 0,
        "validation_failed": 0,
        "needs_review": 0,
        "chunked": 0,
        "chunks_total": 0,
        "skipped": 0,
        "needs_ocr": 0,
    }

    # Phase 1: Manifest scan
    LOGGER.info("Phase 1: Scanning %s (provider=%s, max_files=%s)", root_path, provider, max_files)
    if provider == "local" and root:
        manifests = manifest_mod.scan_local_directory(root, max_files=max_files, provider=provider)
    else:
        return {"error": f"Provider '{provider}' not yet supported for full pipeline", "status": "failed"}

    job.total_files = len(manifests)
    counts["discovered"] = len(manifests)

    if dry_run:
        # Dry run: report discovery only
        supported = sum(1 for m in manifests if m.status != Status.SKIPPED_UNSUPPORTED)
        unsupported = sum(1 for m in manifests if m.status == Status.SKIPPED_UNSUPPORTED)
        job.status = JobStatus.COMPLETED
        job.finished_at = _utc_now()
        counts["skipped"] = unsupported
        return {
            "status": "dry_run_complete",
            "job": _job_summary(job),
            "counts": counts,
            "supported_files": supported,
            "unsupported_files": unsupported,
            "sample_files": [
                {"file": m.file_name, "ext": m.file_ext, "size": m.size_bytes, "status": m.status}
                for m in manifests[:20]
            ],
        }

    # Phase 2–6: Process each file
    errors: list[dict[str, Any]] = []

    try:
        with psycopg.connect(_db_conn(), connect_timeout=60) as conn:
            # Create job record
            job.id = str(uuid.uuid4())
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.digitalization_job (
                        id, provider, root_path, status, started_at, total_files, dry_run, created_by
                    ) VALUES (%s, %s, %s, %s, %s::timestamptz, %s, %s, %s);
                    """,
                    (job.id, job.provider, job.root_path, job.status, job.started_at, job.total_files, job.dry_run, job.created_by),
                )
                conn.commit()

            for i, manifest in enumerate(manifests):
                if manifest.status == Status.SKIPPED_UNSUPPORTED:
                    counts["skipped"] += 1
                    continue

                try:
                    _process_single_file(conn, manifest, root, job, counts)
                except Exception as exc:
                    LOGGER.warning("Error processing %s: %s", manifest.logical_path, exc)
                    counts["extraction_failed"] += 1
                    errors.append({
                        "file": manifest.logical_path,
                        "error": str(exc)[:500],
                    })

                job.processed_files = i + 1

                # Periodic commit
                if (i + 1) % 10 == 0:
                    conn.commit()
                    LOGGER.info("Progress: %d / %d", i + 1, job.total_files)

            # Finalize job
            job.status = JobStatus.COMPLETED
            job.finished_at = _utc_now()
            job.failed_files = counts["extraction_failed"]
            job.error_summary = {"errors": errors[:50]}

            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE platform.digitalization_job SET
                        status = %s, finished_at = %s::timestamptz,
                        processed_files = %s, failed_files = %s,
                        error_summary = %s::jsonb, updated_at = now()
                    WHERE id = %s;
                    """,
                    (job.status, job.finished_at, job.processed_files, job.failed_files,
                     rw._jsonb(job.error_summary), job.id),
                )

            rw.log_event(
                conn,
                event_type="job_completed",
                status=job.status,
                message=f"Processed {job.processed_files} files",
                job_id=job.id,
                details=counts,
            )
            conn.commit()

    except Exception as exc:
        LOGGER.error("Job failed: %s", exc)
        job.status = JobStatus.FAILED
        job.finished_at = _utc_now()
        return {
            "status": "failed",
            "error": str(exc),
            "job": _job_summary(job),
            "counts": counts,
        }

    return {
        "status": "completed",
        "job": _job_summary(job),
        "counts": counts,
        "errors": errors[:20],
    }


def _process_single_file(
    conn,
    manifest: SourceFileManifest,
    root: Path,
    job: DigitalizationJob,
    counts: dict[str, int],
) -> None:
    """Process one file through the full pipeline."""

    # Step 1: Register manifest
    rw.upsert_manifest(conn, manifest)

    # Step 2: Extract
    rw.update_manifest_status(conn, manifest.id, Status.EXTRACTING)
    extracted = extractors.extract_file(manifest, root)
    extracted.manifest_id = manifest.id

    rw.upsert_extracted(conn, extracted)

    if extracted.extraction_status in ("extraction_failed", "needs_ocr"):
        status = Status.EXTRACTION_FAILED if extracted.extraction_status == "extraction_failed" else Status.NEEDS_OCR
        rw.update_manifest_status(conn, manifest.id, status)
        if status == Status.NEEDS_OCR:
            counts["needs_ocr"] += 1
            try:
                from app_skeleton.api.ocr.queue import enqueue_ocr_job

                source_path = str((root / manifest.logical_path).resolve())
                enqueue_ocr_job(
                    conn,
                    manifest_id=manifest.id,
                    extracted_document_id=extracted.id,
                    source_path=source_path,
                    root_path=str(root),
                    metadata={"logical_path": manifest.logical_path, "file_ext": manifest.file_ext},
                )
            except Exception as exc:
                LOGGER.warning("OCR enqueue failed for %s: %s", manifest.logical_path, exc)
        else:
            counts["extraction_failed"] += 1
        return

    rw.update_manifest_status(conn, manifest.id, Status.EXTRACTED)
    counts["extracted"] += 1

    # Step 3: Canonicalize
    rw.update_manifest_status(conn, manifest.id, Status.CANONICALIZING)
    canonical = canonicalizer.canonicalize(manifest, extracted)
    canonical.manifest_id = manifest.id
    canonical.extracted_document_id = extracted.id

    # Step 4: Validate
    validation_status, validation_warnings = validators.validate_canonical(canonical)
    canonical.validation_status = validation_status
    canonical.warnings = validation_warnings

    if validation_status == "validation_failed":
        rw.update_manifest_status(conn, manifest.id, Status.VALIDATION_FAILED)
        canonical.needs_review = True
        rw.upsert_canonical(conn, canonical)
        counts["validation_failed"] += 1
        return

    # Step 5: Register canonical
    rw.upsert_canonical(conn, canonical)
    rw.update_manifest_status(conn, manifest.id, Status.CANONICALIZED)
    counts["canonicalized"] += 1

    if canonical.needs_review:
        counts["needs_review"] += 1

    # Step 6: Chunk
    if canonical.should_index:
        chunks = chunker.chunk_document(manifest, canonical)
        if chunks:
            # Set canonical_document_id on chunks
            for c in chunks:
                c.canonical_document_id = canonical.id
            inserted = rw.insert_chunks(conn, chunks)
            counts["chunked"] += 1
            counts["chunks_total"] += inserted
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
                        },
                    )
            except Exception as exc:
                LOGGER.warning("knowledge_indexer hook failed for %s: %s", manifest.logical_path, exc)


def _job_summary(job: DigitalizationJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "provider": job.provider,
        "root_path": job.root_path,
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "failed_files": job.failed_files,
        "dry_run": job.dry_run,
    }
