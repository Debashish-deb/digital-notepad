#!/usr/bin/env python3
"""OCR queue worker — processes platform.ocr_job rows when ENABLE_OCR=true."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import psycopg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app_skeleton.api.ocr.adapter import get_ocr_backend, ocr_enabled  # noqa: E402
from app_skeleton.api.ocr.queue import apply_ocr_result, resolve_ocr_source_path  # noqa: E402
from app_skeleton.api.sql_migrations import apply_pending_migrations, db_conn  # noqa: E402

LOGGER = logging.getLogger(__name__)


def _conn():
    return psycopg.connect(db_conn(), connect_timeout=15)


def _metadata_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def process_queue(*, limit: int = 10, dry_run: bool = False) -> dict[str, Any]:
    if not ocr_enabled():
        LOGGER.info("ENABLE_OCR=false — worker idle")
        return {"processed": 0, "skipped": "ocr_disabled"}

    backend = get_ocr_backend()
    if backend is None:
        LOGGER.warning("No OCR backend available for OCR_ENGINE")
        return {"processed": 0, "skipped": "no_backend"}

    processed = 0
    failed = 0
    reviewed = 0
    completed = 0
    results: list[dict[str, Any]] = []

    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT job_id, manifest_id, extracted_document_id, source_path, engine, metadata
                FROM platform.ocr_job
                WHERE status = 'queued'
                ORDER BY queued_at
                LIMIT %s
                FOR UPDATE SKIP LOCKED;
                """,
                (limit,),
            )
            jobs = list(cur.fetchall())

        for job_id, manifest_id, extracted_document_id, source_path, engine, metadata in jobs:
            meta = _metadata_dict(metadata)
            job_id_s = str(job_id)

            if dry_run:
                results.append({"job_id": job_id_s, "source_path": source_path, "dry_run": True})
                continue

            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE platform.ocr_job
                    SET status = 'processing', started_at = now(), attempt_count = attempt_count + 1
                    WHERE job_id = %s;
                    """,
                    (job_id,),
                )

            try:
                resolved_path = resolve_ocr_source_path(source_path, meta)
                ocr_result = backend.extract(resolved_path, metadata=meta)
                error = ocr_result.metadata.get("error")
                outcome = apply_ocr_result(
                    conn,
                    job_id=job_id_s,
                    manifest_id=str(manifest_id) if manifest_id else None,
                    extracted_document_id=str(extracted_document_id) if extracted_document_id else None,
                    source_path=source_path,
                    metadata=meta,
                    result_text=ocr_result.text,
                    confidence=ocr_result.confidence,
                    engine=ocr_result.engine or engine or "tesseract",
                    error=str(error) if error else None,
                )
                processed += 1
                job_status = outcome.get("job_status", "unknown")
                if job_status == "failed":
                    failed += 1
                elif job_status == "review":
                    reviewed += 1
                elif job_status == "completed":
                    completed += 1
                results.append({"job_id": job_id_s, **outcome})
            except Exception as exc:
                LOGGER.exception("OCR job %s failed: %s", job_id_s, exc)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE platform.ocr_job SET
                            status = 'failed',
                            error_message = %s,
                            finished_at = now()
                        WHERE job_id = %s;
                        """,
                        (str(exc)[:500], job_id),
                    )
                failed += 1
                results.append({"job_id": job_id_s, "job_status": "failed", "error": str(exc)[:500]})

        conn.commit()

    return {
        "processed": processed,
        "completed": completed,
        "review": reviewed,
        "failed": failed,
        "dry_run": dry_run,
        "results": results[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10, help="Max queued jobs to process")
    parser.add_argument("--dry-run", action="store_true", help="List jobs without OCR")
    parser.add_argument("--apply-migrations", action="store_true", help="Apply pending SQL migrations first")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.apply_migrations:
        applied = apply_pending_migrations()
        if applied:
            LOGGER.info("Applied migrations: %s", applied)

    result = process_queue(limit=args.limit, dry_run=args.dry_run)
    LOGGER.info("Result: %s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
