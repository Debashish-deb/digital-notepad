"""Lab Knowledge Threads — challenge, correct, and refine AI answers (Layer 1)."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from omeia.api.chat_service import answer_chat
from omeia.api.learning_store import schema_available
from omeia.api.platform_flags import lab_knowledge_threads_enabled

LOGGER = logging.getLogger(__name__)


def _threads_schema_ready() -> bool:
    if not schema_available():
        return False
    try:
        from omeia.api.db_pool import get_db_connection

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'platform' AND table_name = 'lab_knowledge_threads' LIMIT 1"
                )
                return cur.fetchone() is not None
    except Exception as exc:
        LOGGER.debug("Thread schema check failed: %s", exc)
        return False


def create_thread(
    *,
    title: str,
    hypothesis: str | None,
    user_email: str,
    initial_query: str | None = None,
    initial_answer: str | None = None,
    response_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not lab_knowledge_threads_enabled():
        return {"ok": False, "error": "disabled"}
    if not _threads_schema_ready():
        return {"ok": False, "error": "schema_unavailable", "hint": "Apply sql/151_lab_knowledge_threads.sql"}

    from omeia.api.db_pool import get_db_connection
    from psycopg.types.json import Jsonb

    thread_id = str(uuid.uuid4())
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO platform.lab_knowledge_threads
                    (thread_id, title, hypothesis, created_by, status, metadata)
                VALUES (%s, %s, %s, %s, 'open', %s)
                """,
                (thread_id, title[:500], hypothesis, user_email, Jsonb(metadata or {})),
            )
            if initial_answer:
                cur.execute(
                    """
                    INSERT INTO platform.lab_knowledge_thread_events
                        (event_id, thread_id, event_type, content, response_id, metadata)
                    VALUES (%s, %s, 'answer', %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        thread_id,
                        initial_answer[:12000],
                        response_id,
                        Jsonb({"query": initial_query}),
                    ),
                )
        conn.commit()
    return {"ok": True, "thread_id": thread_id}


def challenge_thread(
    *,
    thread_id: str,
    challenge_text: str,
    user_email: str,
    user: dict[str, Any],
    llm: Any,
    search_svc: Any,
    rag_agent: Any,
    project_codes: list[str] | None = None,
    agent_category: str | None = None,
) -> dict[str, Any]:
    """Re-retrieve evidence and produce a revised answer after user challenge."""
    if not lab_knowledge_threads_enabled():
        return {"ok": False, "error": "disabled"}
    if not _threads_schema_ready():
        return {"ok": False, "error": "schema_unavailable"}

    from omeia.api.db_pool import get_db_connection
    from psycopg.types.json import Jsonb

    prompt = (
        f"User challenge to prior lab-copilot answer:\n{challenge_text.strip()}\n\n"
        "Re-evaluate using only retrieved internal evidence. State what changed from the prior answer."
    )
    revised = answer_chat(
        prompt,
        project_codes=project_codes,
        user=user,
        agent_category=agent_category,
        llm=llm,
        search_svc=search_svc,
        rag_agent=rag_agent,
    )
    event_id = str(uuid.uuid4())
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO platform.lab_knowledge_thread_events
                    (event_id, thread_id, event_type, content, metadata, created_by)
                VALUES (%s, %s, 'challenge_revision', %s, %s, %s)
                """,
                (
                    event_id,
                    thread_id,
                    (revised.get("answer") or "")[:12000],
                    Jsonb({
                        "challenge": challenge_text[:2000],
                        "sources": revised.get("sources") or [],
                        "expert_route_reason": revised.get("expert_route_reason"),
                        "model": revised.get("model"),
                    }),
                    user_email,
                ),
            )
            cur.execute(
                "UPDATE platform.lab_knowledge_threads SET updated_at = now() WHERE thread_id = %s",
                (thread_id,),
            )
        conn.commit()
    return {
        "ok": True,
        "thread_id": thread_id,
        "event_id": event_id,
        "revised": revised,
    }


def get_thread(thread_id: str) -> dict[str, Any] | None:
    if not _threads_schema_ready():
        return None
    from omeia.api.db_pool import get_db_connection

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT thread_id, title, hypothesis, created_by, status, metadata, created_at, updated_at "
                "FROM platform.lab_knowledge_threads WHERE thread_id = %s",
                (thread_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cur.execute(
                "SELECT event_id, event_type, content, response_id, metadata, created_by, created_at "
                "FROM platform.lab_knowledge_thread_events WHERE thread_id = %s ORDER BY created_at ASC",
                (thread_id,),
            )
            events = cur.fetchall()
    cols = ["thread_id", "title", "hypothesis", "created_by", "status", "metadata", "created_at", "updated_at"]
    thread = dict(zip(cols, row))
    thread["events"] = [
        dict(zip(["event_id", "event_type", "content", "response_id", "metadata", "created_by", "created_at"], e))
        for e in events
    ]
    return thread
