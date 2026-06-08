#!/usr/bin/env python3
"""Enqueue and process vault vectorization jobs (LUMI-W130).

Only rows with vector_status=eligible_pending_review are queued.
OME-TIFF and other image slides stay metadata_summary_only and are never queued.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app_skeleton.api.sql_migrations import apply_pending_migrations, db_conn  # noqa: E402

ELIGIBLE_STATUS = "eligible_pending_review"
BLOCKED_IMAGE_MIMES = ("image/tiff", "image/tif", "application/ome-tiff")


def _conn():
    return psycopg.connect(db_conn(), connect_timeout=15)


def enqueue_eligible(*, limit: int) -> dict:
    created = 0
    skipped = 0
    rows: list = []
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT asset_id, logical_path, mime_type, vector_status
                FROM platform.raw_asset_vault
                WHERE vector_status = %s
                ORDER BY indexed_at DESC NULLS LAST
                LIMIT %s;
                """,
                (ELIGIBLE_STATUS, limit),
            )
            rows = list(cur.fetchall())
            for asset_id, logical_path, mime_type, vector_status in rows:
                mime = (mime_type or "").lower()
                path_low = (logical_path or "").lower()
                blocked_reason = None
                if mime in BLOCKED_IMAGE_MIMES or path_low.endswith((".ome.tiff", ".ome.tif")):
                    blocked_reason = "ome_tiff_not_vectorized"
                elif mime.startswith("image/") and path_low.endswith((".tif", ".tiff")):
                    blocked_reason = "image_metadata_only"

                if blocked_reason:
                    cur.execute(
                        """
                        INSERT INTO platform.vectorization_job (asset_id, status, blocked_reason, finished_at)
                        VALUES (%s, 'blocked', %s, now());
                        """,
                        (asset_id, blocked_reason),
                    )
                    skipped += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO platform.vectorization_job (asset_id, status)
                    SELECT %s, 'queued'
                    WHERE NOT EXISTS (
                      SELECT 1 FROM platform.vectorization_job j
                      WHERE j.asset_id = %s AND j.status IN ('queued', 'running')
                    );
                    """,
                    (asset_id, asset_id),
                )
                if cur.rowcount:
                    created += 1
        conn.commit()
    return {"queued": created, "blocked": skipped, "candidates": len(rows)}


def process_queued(*, limit: int) -> dict:
    """Process queued vectorization jobs; honors VECTORIZATION_ENABLED (no fake vectors)."""
    enabled = os.environ.get("VECTORIZATION_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on",
    }
    done = 0
    disabled = 0
    with _conn() as conn:
        with conn.cursor() as cur:
            if not enabled:
                cur.execute(
                    """
                    UPDATE platform.raw_asset_vault
                    SET vector_status = 'disabled'
                    WHERE vector_status = %s;
                    """,
                    (ELIGIBLE_STATUS,),
                )
                disabled = cur.rowcount
                cur.execute(
                    """
                    UPDATE platform.vectorization_job
                    SET status = 'blocked', blocked_reason = 'VECTORIZATION_ENABLED=false', finished_at = now()
                    WHERE status = 'queued';
                    """
                )
                conn.commit()
                return {"processed": 0, "disabled_assets": disabled, "vectorization_enabled": False}

            cur.execute(
                """
                SELECT job_id, asset_id FROM platform.vectorization_job
                WHERE status = 'queued'
                ORDER BY created_at
                LIMIT %s
                FOR UPDATE SKIP LOCKED;
                """,
                (limit,),
            )
            jobs = cur.fetchall()
            for job_id, asset_id in jobs:
                cur.execute(
                    "UPDATE platform.vectorization_job SET status = 'running' WHERE job_id = %s;",
                    (job_id,),
                )
                cur.execute(
                    """
                    UPDATE platform.raw_asset_vault
                    SET vector_status = 'pending'
                    WHERE asset_id = %s AND vector_status = %s;
                    """,
                    (asset_id, ELIGIBLE_STATUS),
                )
                cur.execute(
                    """
                    UPDATE platform.vectorization_job
                    SET status = 'completed', blocked_reason = 'deferred_to_vault_ingestion_engine', finished_at = now()
                    WHERE job_id = %s;
                    """,
                    (job_id,),
                )
                done += 1
        conn.commit()
    return {"processed": done, "vectorization_enabled": True, "note": "Use vault ingest with VECTORIZATION_ENABLED=true for embeddings"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enqueue", type=int, default=0, metavar="N")
    parser.add_argument("--process", type=int, default=0, metavar="N")
    args = parser.parse_args()

    apply_pending_migrations()
    if args.enqueue:
        print(enqueue_eligible(limit=args.enqueue))
    if args.process:
        print(process_queued(limit=args.process))
    if not args.enqueue and not args.process:
        print(enqueue_eligible(limit=50))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
