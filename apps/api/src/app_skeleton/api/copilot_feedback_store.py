"""Persist copilot thumbs / corrections for eval pipeline."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import psycopg

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


def save_feedback(
    *,
    user_email: str,
    query_text: str,
    answer_excerpt: str | None,
    rating: int,
    correction_note: str | None = None,
    session_id: str | None = None,
    intent: str | None = None,
    project_codes: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    rating = max(-1, min(1, int(rating)))
    try:
        with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.copilot_feedback (
                        user_email, session_id, query_text, answer_excerpt,
                        rating, correction_note, intent, project_codes, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING feedback_id::text;
                    """,
                    (
                        user_email,
                        session_id,
                        query_text[:4000],
                        (answer_excerpt or "")[:4000] or None,
                        rating,
                        (correction_note or "")[:2000] or None,
                        intent,
                        list(project_codes or []),
                        json.dumps(metadata or {}),
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return row[0] if row else None
    except Exception as exc:
        LOGGER.warning("copilot_feedback save failed: %s", exc)
        return None


def export_feedback_to_eval_csv(
    dest: Path | None = None,
    *,
    limit: int = 500,
) -> Path | None:
    """Append recent negative/neutral feedback as eval question stubs."""
    dest = dest or (ROOT / "tests" / "feedback_export_stub.csv")
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT query_text, correction_note, rating, created_at::text
                    FROM platform.copilot_feedback
                    WHERE rating <= 0
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
    except Exception as exc:
        LOGGER.warning("feedback export failed: %s", exc)
        return None

    if not rows:
        return None

    lines = ["question,expected_note,rating,created_at"]
    for q, note, rating, created in rows:
        safe_q = (q or "").replace('"', '""')
        safe_n = (note or "").replace('"', '""')
        lines.append(f'"{safe_q}","{safe_n}",{rating},{created}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest
