"""Shared retrieval context for category agent runs."""
from __future__ import annotations

import os
from typing import Any, Callable

from omeia.api.chat_conversation import classify_and_enrich
from omeia.api.evidence_orchestrator import understand_query


def _format_library_scope(library_scope: dict[str, Any] | None) -> str:
    if not library_scope:
        return ""
    parts = [
        "Current document library view:",
        f"- Section: {library_scope.get('scope_label') or library_scope.get('main_id')}/{library_scope.get('sub_id')}",
        f"- Domain tab: {library_scope.get('domain_tab')}",
    ]
    filters = library_scope.get("filters") or {}
    if filters:
        parts.append(f"- Active filters: {filters}")
    summary = library_scope.get("scope_summary")
    if summary:
        parts.append(summary)
    parts.append(
        "When answering, prefer files matching this scope. "
        "Protocol questions should cite is_protocol files; reagent/panel questions should cite is_reagent_panel files."
    )
    return "\n".join(parts)


def build_rag_bundle(
    message: str,
    *,
    project_codes: list[str] | None,
    search_svc: Any,
    rag_agent: Any,
    max_sources: int | None = None,
    library_scope: dict[str, Any] | None = None,
    user_role: str | None = None,
) -> dict[str, Any]:
    limit = max_sources or int(os.getenv("CHAT_MAX_SOURCES", "12") or "12")
    intent = classify_and_enrich(message)
    if not intent.use_rag:
        return {"retrieval_context": "", "sources": [], "search_hits": [], "limitations": []}

    understanding = understand_query(message, intent)
    hits = search_svc.hits_for_copilot(
        message,
        intent=intent.intent,
        project_codes=project_codes,
        limit=limit,
        prioritize_buckets=understanding.search_plan.prioritize_buckets,
        user_role=user_role,
    )
    sources: list[dict[str, Any]] = []
    lines: list[str] = []
    for i, hit in enumerate(hits[:limit], start=1):
        title = getattr(hit, "title", None) or getattr(hit, "name", None) or "Source"
        excerpt = getattr(hit, "excerpt", None) or getattr(hit, "snippet", None) or ""
        lines.append(f"{i}. {title}: {str(excerpt)[:500]}")
        if hasattr(hit, "model_dump"):
            sources.append(hit.model_dump())
        elif isinstance(hit, dict):
            sources.append(hit)

    rag_sources = []
    if len(hits) < max(3, limit // 2):
        try:
            rag_sources = rag_agent.retrieve(message, project_codes)
        except Exception:
            rag_sources = []

    scope_block = _format_library_scope(library_scope)
    ctx = "\n".join(lines)
    if not ctx and not scope_block:
        return {
            "retrieval_context": "",
            "sources": [],
            "search_hits": [h.model_dump() if hasattr(h, "model_dump") else h for h in hits],
            "limitations": ["No matching documents retrieved for this question."],
        }
    retrieval = "\n\n".join(block for block in (scope_block, f"Retrieved lab knowledge:\n{ctx}" if ctx else "") if block)
    return {
        "retrieval_context": retrieval,
        "sources": sources,
        "search_hits": [h.model_dump() if hasattr(h, "model_dump") else h for h in hits],
        "limitations": [],
    }
