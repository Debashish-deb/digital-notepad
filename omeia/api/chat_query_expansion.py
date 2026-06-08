"""Expand short or follow-up chat turns into retrieval-friendly queries."""
from __future__ import annotations

import re
from typing import Any

from omeia.api.chat_session_store import SessionContext

_TELL_MORE_RE = re.compile(r"^tell me more about:\s*(.+)$", re.I)
_FOLLOWUP_RE = re.compile(
    r"^\s*(?:tell me more|more about|what about|explain (?:that|this|it)|go deeper|"
    r"can you elaborate|follow[- ]?up|why is that|how does that|and what about|"
    r"anything else|expand on|clarify|same for|compare with|versus|vs\.?)\b",
    re.I,
)
_PRONOUN_LEAD_RE = re.compile(r"^\s*(?:that|this|it|those|them|there|the same)\b", re.I)
_VAGUE_SHORT_RE = re.compile(
    r"^\s*(?:yes|no|ok|okay|sure|why|how|when|where|who|which one|next|continue)\s*[?!.]*\s*$",
    re.I,
)


def _normalize_history(client_history: list[dict[str, Any]] | None) -> list[tuple[str, str]]:
    if not client_history:
        return []
    turns: list[tuple[str, str]] = []
    for item in client_history:
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            turns.append((role, content))
    return turns[-12:]


def _merge_turns(
    session_ctx: SessionContext | None,
    client_history: list[dict[str, Any]] | None,
) -> list[tuple[str, str]]:
    if session_ctx and session_ctx.recent_turns:
        return list(session_ctx.recent_turns)
    return _normalize_history(client_history)


def _last_user_question(turns: list[tuple[str, str]]) -> str:
    for role, content in reversed(turns):
        if role == "user" and len(content.strip()) >= 8:
            return content.strip()
    return ""


def _last_assistant_excerpt(turns: list[tuple[str, str]], *, max_len: int = 280) -> str:
    for role, content in reversed(turns):
        if role == "assistant" and not content.startswith("Good morning"):
            text = content.strip().replace("\n", " ")
            if len(text) > max_len:
                return text[:max_len].rsplit(" ", 1)[0]
            return text
    return ""


def _needs_context_expansion(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    if _TELL_MORE_RE.match(text):
        return True
    if len(text) <= 48 and (_FOLLOWUP_RE.search(text) or _PRONOUN_LEAD_RE.search(text) or _VAGUE_SHORT_RE.match(text)):
        return True
    if len(text) <= 24:
        return True
    return False


def enrich_query_with_library_scope(query: str, library_scope: dict[str, Any] | None) -> str:
    if not library_scope:
        return query
    label = str(library_scope.get("scope_label") or "").strip()
    domain = str(library_scope.get("domain_tab") or "").strip()
    if not label and not domain:
        return query
    scope_hint = " ".join(part for part in (label, domain) if part)
    lower = query.lower()
    if scope_hint and scope_hint.lower() not in lower:
        return f"{query} (document library scope: {scope_hint})"
    return query


def build_contextual_retrieval_query(
    message: str,
    *,
    session_ctx: SessionContext | None = None,
    client_history: list[dict[str, Any]] | None = None,
) -> tuple[str, str | None]:
    """
    Return (retrieval_query, expansion_note).
    The original message is still used for synthesis; retrieval may be expanded.
    """
    text = (message or "").strip()
    if not text:
        return text, None

    tell_more = _TELL_MORE_RE.match(text)
    if tell_more:
        topic = tell_more.group(1).strip()
        return topic, "source_follow_up"

    if not _needs_context_expansion(text):
        return text, None

    turns = _merge_turns(session_ctx, client_history)
    if not turns:
        return text, None

    prior_user = _last_user_question(turns)
    prior_answer = _last_assistant_excerpt(turns)
    if not prior_user:
        return text, None

    parts = [prior_user]
    if text.lower() not in prior_user.lower():
        parts.append(text)
    if prior_answer and len(prior_answer) > 40:
        parts.append(prior_answer)

    expanded = " ".join(part.strip() for part in parts if part.strip())
    if expanded.lower() == text.lower():
        return text, None
    return expanded[:900], "conversation_context"
