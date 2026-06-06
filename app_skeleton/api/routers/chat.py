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

_STREAM_INTERNAL_KEYS = frozenset({"system_prompt", "user_content"})


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
    intent: str = "general_chat"
    use_rag: bool = False
    show_sources: bool = False
    require_citations: bool = False
    answer_style: str = "natural"
    reason: str = ""


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


def _public_chat_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in result.items() if k not in _STREAM_INTERNAL_KEYS}


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
    require_role(user, ["researcher", "viewer", "editor", "admin"])
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
    return ChatResponse(**_public_chat_payload(result))


def _sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
def chat_stream(req: ChatRequest, user: dict = Depends(require_platform_user)) -> StreamingResponse:
    require_role(user, ["researcher", "viewer", "editor", "admin"])
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
    public_base = _public_chat_payload(base)
    system_prompt = base.get("system_prompt", "")
    user_content = base.get("user_content", req.message)

    if base.get("blocked_by_guardrail"):
        def blocked_iter() -> Iterator[str]:
            yield _sse_event({"type": "metadata", **{k: public_base[k] for k in ("sources", "search_hits", "limitations", "provider", "is_safe", "intent", "show_sources")}})
            yield _sse_event({"type": "delta", "content": public_base.get("answer", "")})
            yield _sse_event({"type": "done"})
        return StreamingResponse(blocked_iter(), media_type="text/event-stream")

    def event_iter() -> Iterator[str]:
        yield _sse_event({
            "type": "metadata",
            "sources": public_base.get("sources", []),
            "search_hits": public_base.get("search_hits", []),
            "limitations": public_base.get("limitations", []),
            "provider": public_base.get("provider", active_llm.provider),
            "database_counts": public_base.get("database_counts", {}),
            "is_safe": public_base.get("is_safe", True),
            "intent": public_base.get("intent", "general_chat"),
            "show_sources": public_base.get("show_sources", False),
        })
        try:
            for delta in active_llm.stream_generate(user_content, system_prompt):
                if delta:
                    yield _sse_event({"type": "delta", "content": delta})
        except Exception as exc:
            LOGGER.warning("Chat stream failed, falling back to buffered answer: %s", exc)
            yield _sse_event({"type": "delta", "content": public_base.get("answer", "")})
        yield _sse_event({"type": "done"})

    return StreamingResponse(event_iter(), media_type="text/event-stream")
