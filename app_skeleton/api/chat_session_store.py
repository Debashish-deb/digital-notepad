"""Conversation memory — Postgres chat_session + chat_turn."""
from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any

import psycopg

LOGGER = logging.getLogger(__name__)


def sessions_enabled() -> bool:
    return os.getenv("CHAT_SESSION_MEMORY", "true").strip().lower() in {"1", "true", "yes", "on"}


def _max_turns() -> int:
    return max(2, min(int(os.getenv("CHAT_SESSION_MAX_TURNS", "12") or 12), 40))


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


@dataclass(frozen=True)
class SessionContext:
    session_id: str
    summary: str
    recent_turns: tuple[tuple[str, str], ...]


def _table_exists(cur, table: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'platform' AND table_name = %s
        LIMIT 1;
        """,
        (table.split(".")[-1],),
    )
    return cur.fetchone() is not None


def ensure_session(
    *,
    session_id: str | None,
    user_email: str,
    project_codes: list[str] | None,
) -> str:
    if not sessions_enabled() or not user_email:
        return session_id or ""
    sid = (session_id or "").strip()
    codes = list(project_codes or [])
    try:
        with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
            with conn.cursor() as cur:
                if not _table_exists(cur, "chat_session"):
                    return sid
                if sid:
                    cur.execute(
                        "SELECT session_id FROM platform.chat_session WHERE session_id = %s::uuid AND user_email = %s;",
                        (sid, user_email),
                    )
                    if cur.fetchone():
                        return sid
                new_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO platform.chat_session (session_id, user_email, project_codes)
                    VALUES (%s::uuid, %s, %s);
                    """,
                    (new_id, user_email, codes),
                )
                conn.commit()
                return new_id
    except Exception as exc:
        LOGGER.debug("chat_session ensure failed: %s", exc)
        return sid


def load_session_context(session_id: str | None, *, user_email: str) -> SessionContext | None:
    if not sessions_enabled() or not session_id or not user_email:
        return None
    try:
        with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
            with conn.cursor() as cur:
                if not _table_exists(cur, "chat_session"):
                    return None
                cur.execute(
                    """
                    SELECT summary FROM platform.chat_session
                    WHERE session_id = %s::uuid AND user_email = %s;
                    """,
                    (session_id, user_email),
                )
                row = cur.fetchone()
                if not row:
                    return None
                summary = (row[0] or "").strip()
                cur.execute(
                    """
                    SELECT role, content FROM platform.chat_turn
                    WHERE session_id = %s::uuid
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    (session_id, _max_turns()),
                )
                turns = list(reversed(cur.fetchall()))
                return SessionContext(
                    session_id=session_id,
                    summary=summary,
                    recent_turns=tuple((r[0], r[1]) for r in turns),
                )
    except Exception as exc:
        LOGGER.debug("chat_session load failed: %s", exc)
        return None


def format_memory_block(ctx: SessionContext | None) -> str:
    if not ctx:
        return ""
    parts: list[str] = []
    if ctx.summary:
        parts.append(f"Session summary: {ctx.summary[:1200]}")
    if ctx.recent_turns:
        parts.append("Recent turns:")
        for role, content in ctx.recent_turns[-6:]:
            parts.append(f"- {role}: {str(content)[:400]}")
    if not parts:
        return ""
    return "\n".join(parts) + "\n\nUse this conversation context for follow-up consistency. Do not invent facts not in sources.\n"


def append_turn(
    session_id: str,
    *,
    user_email: str,
    role: str,
    content: str,
    intent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not sessions_enabled() or not session_id or not content.strip():
        return
    try:
        with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
            with conn.cursor() as cur:
                if not _table_exists(cur, "chat_turn"):
                    return
                cur.execute(
                    """
                    INSERT INTO platform.chat_turn (session_id, role, content, intent, metadata)
                    VALUES (%s::uuid, %s, %s, %s, %s::jsonb);
                    """,
                    (session_id, role, content[:8000], intent, json.dumps(metadata or {})),
                )
                cur.execute(
                    """
                    UPDATE platform.chat_session
                    SET turn_count = turn_count + 1, updated_at = now()
                    WHERE session_id = %s::uuid AND user_email = %s;
                    """,
                    (session_id, user_email),
                )
                conn.commit()
        maybe_refresh_session_summary(session_id, user_email=user_email)
    except Exception as exc:
        LOGGER.debug("chat_turn append failed: %s", exc)


def maybe_refresh_session_summary(session_id: str, *, user_email: str) -> None:
    """Extractive session summary when turn volume exceeds the rolling window."""
    if not sessions_enabled() or not session_id or not user_email:
        return
    compress_after = max(_max_turns() + 2, _max_turns() * 2)
    try:
        with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
            with conn.cursor() as cur:
                if not _table_exists(cur, "chat_session"):
                    return
                cur.execute(
                    """
                    SELECT turn_count FROM platform.chat_session
                    WHERE session_id = %s::uuid AND user_email = %s;
                    """,
                    (session_id, user_email),
                )
                row = cur.fetchone()
                if not row or int(row[0] or 0) < compress_after:
                    return
                cur.execute(
                    """
                    SELECT role, content FROM platform.chat_turn
                    WHERE session_id = %s::uuid
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    (session_id, compress_after),
                )
                turns = list(reversed(cur.fetchall()))
        bullets: list[str] = []
        for role, content in turns:
            text = str(content or "").strip().replace("\n", " ")
            if not text:
                continue
            if role == "user":
                bullets.append(f"User asked: {text[:220]}")
            else:
                first = text.split(". ")[0][:180]
                bullets.append(f"Assistant: {first}")
        if not bullets:
            return
        summary = " | ".join(bullets[-10:])
        refresh_summary(session_id, user_email=user_email, summary=summary)
    except Exception as exc:
        LOGGER.debug("session summary compress failed: %s", exc)


def refresh_summary(session_id: str, *, user_email: str, summary: str) -> None:
    if not sessions_enabled() or not session_id or not summary.strip():
        return
    try:
        with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE platform.chat_session
                    SET summary = %s, updated_at = now()
                    WHERE session_id = %s::uuid AND user_email = %s;
                    """,
                    (summary[:4000], session_id, user_email),
                )
                conn.commit()
    except Exception as exc:
        LOGGER.debug("chat_session summary update failed: %s", exc)
