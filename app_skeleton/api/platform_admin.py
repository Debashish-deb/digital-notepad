"""Administration APIs — allowlist, jobs, review (LUMI-W150)."""
from __future__ import annotations

import json
import os
import uuid
from typing import Any

import psycopg


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


DEFAULT_PLATFORM_ADMIN_EMAILS: tuple[str, ...] = (
    "anniina.farkkila@helsinki.fi",
    "debashish.deb@helsinki.fi",
    "joonas.jukonen@helsinki.fi",
)


def platform_admin_emails() -> set[str]:
    """Emails with platform admin role (registration approve, allowlist CRUD)."""
    raw = os.getenv("PLATFORM_ADMIN_EMAILS", "").strip()
    if raw:
        return {e.strip().lower() for e in raw.split(",") if e.strip()}
    return {e.lower() for e in DEFAULT_PLATFORM_ADMIN_EMAILS}


def is_platform_admin(email: str | None) -> bool:
    return bool(email) and email.strip().lower() in platform_admin_emails()


def list_allowed_emails() -> list[dict[str, Any]]:
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, status, approved_by, approved_at FROM platform.allowed_email ORDER BY email;"
            )
            return [
                {"email": r[0], "status": r[1], "approved_by": r[2], "approved_at": str(r[3]) if r[3] else None}
                for r in cur.fetchall()
            ]


def upsert_allowed_email(email: str, *, status: str = "approved", approved_by: str | None = None) -> dict[str, Any]:
    email = email.strip().lower()
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO platform.allowed_email (email, status, approved_by, approved_at)
                VALUES (%s, %s, %s, CASE WHEN %s = 'approved' THEN now() ELSE NULL END)
                ON CONFLICT (email) DO UPDATE SET
                    status = EXCLUDED.status,
                    approved_by = EXCLUDED.approved_by,
                    approved_at = CASE WHEN EXCLUDED.status = 'approved' THEN now() ELSE platform.allowed_email.approved_at END;
                """,
                (email, status, approved_by, status),
            )
        conn.commit()
    return {"email": email, "status": status}


def list_registration_requests(*, status: str | None = "pending") -> list[dict[str, Any]]:
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            if status:
                cur.execute(
                    """
                    SELECT request_id, email, display_name, status, requested_at
                    FROM platform.registration_request WHERE status = %s ORDER BY requested_at DESC;
                    """,
                    (status,),
                )
            else:
                cur.execute(
                    """
                    SELECT request_id, email, display_name, status, requested_at
                    FROM platform.registration_request ORDER BY requested_at DESC LIMIT 100;
                    """
                )
            return [
                {
                    "request_id": str(r[0]),
                    "email": r[1],
                    "display_name": r[2],
                    "status": r[3],
                    "requested_at": str(r[4]),
                }
                for r in cur.fetchall()
            ]


def list_ingestion_jobs(*, limit: int = 20) -> list[dict[str, Any]]:
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT job_id, job_type, status, items_total, items_processed, started_at, finished_at, created_at
                FROM platform.ingestion_job ORDER BY created_at DESC LIMIT %s;
                """,
                (limit,),
            )
            return [
                {
                    "job_id": str(r[0]),
                    "job_type": r[1],
                    "status": r[2],
                    "items_total": r[3],
                    "items_processed": r[4],
                    "started_at": str(r[5]) if r[5] else None,
                    "finished_at": str(r[6]) if r[6] else None,
                    "created_at": str(r[7]),
                }
                for r in cur.fetchall()
            ]


def create_ingestion_job(job_type: str, *, items_total: int = 0, config: dict | None = None) -> dict[str, Any]:
    job_id = uuid.uuid4()
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO platform.ingestion_job (job_id, job_type, status, items_total, config, started_at)
                VALUES (%s, %s, 'running', %s, %s::jsonb, now());
                """,
                (job_id, job_type, items_total, json.dumps(config or {})),
            )
        conn.commit()
    return {"job_id": str(job_id), "job_type": job_type, "status": "running"}


def finish_ingestion_job(
    job_id: str,
    *,
    status: str = "completed",
    items_processed: int | None = None,
    error_summary: str | None = None,
) -> None:
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE platform.ingestion_job
                SET status = %s,
                    items_processed = COALESCE(%s, items_processed),
                    error_summary = %s,
                    finished_at = now()
                WHERE job_id = %s;
                """,
                (status, items_processed, error_summary, job_id),
            )
        conn.commit()


def list_review_tasks(*, status: str = "open", limit: int = 50) -> list[dict[str, Any]]:
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT task_id, asset_id, task_type, status, assignment_confidence, sensitivity_level, created_at
                FROM platform.review_task
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (status, limit),
            )
            return [
                {
                    "task_id": str(r[0]),
                    "asset_id": r[1],
                    "task_type": r[2],
                    "status": r[3],
                    "assignment_confidence": float(r[4]) if r[4] is not None else None,
                    "sensitivity_level": r[5],
                    "created_at": str(r[6]),
                }
                for r in cur.fetchall()
            ]
