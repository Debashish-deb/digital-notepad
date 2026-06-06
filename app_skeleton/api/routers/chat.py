"""Gemini Research Copilot chat API — status, JSON, and SSE streaming."""
from __future__ import annotations

import json
import os
from typing import Any, Iterator, List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app_skeleton.api.chat_service import answer_chat
from app_skeleton.api.common import LOGGER, SourceInfo, llm_client, qdrant_client, rag_agent, DB_CONN
from app_skeleton.api.llm_client import LLMClient
from app_skeleton.api.search_service import SearchService
from app_skeleton.security.auth import require_platform_user
from app_skeleton.security.permissions import require_role

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    project_codes: List[str] = Field(default_factory=list)
    stream: bool = False


class ChatResponse(BaseModel):
    answer: str
    limitations: List[str] = Field(default_factory=list)
    sources: List[SourceInfo] = Field(default_factory=list)
    database_counts: dict[str, Any] = Field(default_factory=dict)
    is_safe: bool = True
    search_hits: List[dict[str, Any]] = Field(default_factory=list)
    provider: str = "mock"
    blocked_by_guardrail: bool = False


def _chat_llm() -> LLMClient:
    """Resolve chat-specific provider without exposing secrets to callers."""
    chat_provider = os.getenv("CHAT_LLM_PROVIDER", "").strip().lower()
    if not chat_provider:
        return llm_client

    active = LLMClient()
    active.provider = chat_provider
    active._init_client()
    return active


def _search_service(active_llm: LLMClient) -> SearchService:
    return SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=active_llm)


@router.get("/status")
def chat_status(user: dict = Depends(require_platform_user)) -> dict[str, Any]:
    active = _chat_llm()
    return {
        "chat_provider": active.provider,
        "chat_model": active.model,
        "stream_enabled": os.getenv("CHAT_STREAM_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
        "max_sources": int(os.getenv("CHAT_MAX_SOURCES", "12") or "12"),
        "llm": active.public_status(),
    }


@router.post("", response_model=ChatResponse)
def chat_message(req: ChatRequest, user: dict = Depends(require_platform_user)) -> ChatResponse:
    require_role(user, ["editor", "admin"])
    active_llm = _chat_llm()
    search_svc = _search_service(active_llm)

    result = answer_chat(
        req.message,
        project_codes=req.project_codes,
        user=user,
        llm=active_llm,
        search_svc=search_svc,
        rag_agent=rag_agent,
    )
    return ChatResponse(**result)


def _sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
def chat_stream(req: ChatRequest, user: dict = Depends(require_platform_user)) -> StreamingResponse:
    require_role(user, ["editor", "admin"])
    active_llm = _chat_llm()
    search_svc = _search_service(active_llm)

    base = answer_chat(
        req.message,
        project_codes=req.project_codes,
        user=user,
        llm=active_llm,
        search_svc=search_svc,
        rag_agent=rag_agent,
    )

    if base.get("blocked_by_guardrail"):
        def blocked_iter() -> Iterator[str]:
            yield _sse_event({"type": "metadata", **{k: base[k] for k in ("sources", "search_hits", "limitations", "provider", "is_safe")}})
            yield _sse_event({"type": "delta", "content": base.get("answer", "")})
            yield _sse_event({"type": "done"})
        return StreamingResponse(blocked_iter(), media_type="text/event-stream")

    # Rebuild prompts for streaming (answer_chat already retrieved context).
    from app_skeleton.api.chat_service import _build_prompts, _hits_to_sources, guard_for_llm
    from app_skeleton.api.common import _clinical_context_for_question, query_postgres_metadata

    safe_message, _, _ = guard_for_llm(req.message, active_llm.provider)
    db_data = query_postgres_metadata(req.project_codes)
    clinical_block = _clinical_context_for_question(safe_message, req.project_codes or [])
    unified_hits = search_svc.hits_for_copilot(safe_message, project_codes=req.project_codes, limit=12)
    rag_sources = rag_agent.retrieve(safe_message, req.project_codes)
    retrieved_sources, unified_hits = _hits_to_sources(unified_hits, rag_sources, limit=12)
    system_prompt, user_content = _build_prompts(
        question=safe_message,
        unified_hits=unified_hits,
        rag_sources=rag_sources,
        db_data=db_data,
        clinical_block=clinical_block,
        sources=retrieved_sources,
    )

    def event_iter() -> Iterator[str]:
        yield _sse_event({
            "type": "metadata",
            "sources": base.get("sources", []),
            "search_hits": base.get("search_hits", []),
            "limitations": base.get("limitations", []),
            "provider": base.get("provider", active_llm.provider),
            "database_counts": base.get("database_counts", {}),
            "is_safe": base.get("is_safe", True),
        })
        try:
            for delta in active_llm.stream_generate(user_content, system_prompt):
                if delta:
                    yield _sse_event({"type": "delta", "content": delta})
        except Exception as exc:
            LOGGER.warning("Chat stream failed, falling back to buffered answer: %s", exc)
            yield _sse_event({"type": "delta", "content": base.get("answer", "")})
        yield _sse_event({"type": "done"})

    return StreamingResponse(event_iter(), media_type="text/event-stream")
