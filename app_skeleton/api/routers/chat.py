"""Gemini Research Copilot chat API — status, JSON, and SSE streaming."""
from __future__ import annotations

import json
import os
from typing import Any, Iterator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app_skeleton.api.chat_model_catalog import build_chat_model_catalog, make_chat_llm
from app_skeleton.api.agent_orchestrator.registry import list_visible_categories, load_categories_config
from app_skeleton.api.chat_service import answer_chat
from app_skeleton.api.rag_diagnostics import run_rag_diagnostics
from app_skeleton.api.common import LOGGER, SourceInfo, llm_client, qdrant_client, rag_agent, DB_CONN
from app_skeleton.api.llm_client import LLMClient, _env
from app_skeleton.api.search_service import SearchService
from app_skeleton.security.auth import require_platform_user
from app_skeleton.security.permissions import require_role

router = APIRouter(prefix="/api/chat", tags=["chat"])

_STREAM_INTERNAL_KEYS = frozenset({"system_prompt", "user_content"})


class ChatRequest(BaseModel):
    message: str
    project_codes: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    stream: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None


class ChatFeedbackRequest(BaseModel):
    query_text: str
    answer_excerpt: str = ""
    rating: int = Field(..., ge=-1, le=1)
    correction_note: str = ""
    session_id: Optional[str] = None
    intent: Optional[str] = None
    project_codes: List[str] = Field(default_factory=list)


class RagDebugRequest(BaseModel):
    query: str
    project_codes: List[str] = Field(default_factory=list)
    category: str = "cancer_oncology"
    mode: str = "balanced"
    probe_llm: bool = True


class ChatResponse(BaseModel):
    answer: str
    limitations: List[str] = Field(default_factory=list)
    sources: List[SourceInfo] = Field(default_factory=list)
    database_counts: dict[str, Any] = Field(default_factory=dict)
    is_safe: bool = True
    search_hits: List[dict[str, Any]] = Field(default_factory=list)
    provider: str = "mock"
    effective_provider: str = "mock"
    model: str = "mock-model"
    fallback_used: bool = False
    synthesis_mode: str = "mock"
    blocked_by_guardrail: bool = False
    intent: str = "general_chat"
    intent_category: str = "GENERAL_CHAT"
    confidence: float = 0.7
    use_rag: bool = False
    show_sources: bool = False
    require_citations: bool = False
    answer_style: str = "natural"
    reason: str = ""
    evidence_orchestrator: bool = False
    query_domains: List[str] = Field(default_factory=list)
    query_entities: List[str] = Field(default_factory=list)
    search_plan: Optional[dict[str, Any]] = None
    evidence_confidence: Optional[str] = None
    evidence_buckets: Optional[dict[str, int]] = None
    evidence_count: Optional[int] = None
    cross_source_summary: Optional[str] = None
    evidence_validation_notes: List[str] = Field(default_factory=list)
    claim_validations: List[dict[str, Any]] = Field(default_factory=list)
    response_sections: List[dict[str, Any]] = Field(default_factory=list)
    session_id: Optional[str] = None
    answer_regenerated: bool = False


_ORCHESTRATOR_SSE_KEYS = (
    "evidence_orchestrator",
    "query_domains",
    "query_entities",
    "search_plan",
    "evidence_confidence",
    "evidence_buckets",
    "evidence_count",
    "cross_source_summary",
    "evidence_validation_notes",
    "claim_validations",
    "response_sections",
    "intent_category",
    "confidence",
    "use_rag",
    "show_sources",
    "require_citations",
    "answer_style",
    "synthesis_mode",
)


def _chat_llm(provider: Optional[str] = None, model: Optional[str] = None) -> LLMClient:
    return make_chat_llm(provider, model, default_llm=llm_client)


def _search_service(active_llm: LLMClient) -> SearchService:
    return SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=active_llm)


def _public_chat_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in result.items() if k not in _STREAM_INTERNAL_KEYS}


@router.post("/rag-debug")
def chat_rag_debug(
    req: RagDebugRequest,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    """Timed in-process RAG wiring diagnostics (dev/troubleshooting)."""
    require_role(user, ["researcher", "viewer", "editor", "admin"])
    active_llm = _chat_llm(None, None)
    search_svc = _search_service(active_llm)
    report = run_rag_diagnostics(
        req.query,
        search_svc=search_svc,
        llm=active_llm,
        rag_agent=rag_agent,
        project_codes=req.project_codes,
        category_id=req.category,
        mode=req.mode,
        probe_llm=req.probe_llm,
    )
    return report.to_dict()


@router.post("/feedback")
def chat_feedback(
    req: ChatFeedbackRequest,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    """Thumbs up/down and optional correction note for eval pipeline."""
    require_role(user, ["researcher", "viewer", "editor", "admin"])
    from app_skeleton.api.copilot_feedback_store import save_feedback

    feedback_id = save_feedback(
        user_email=user.get("email") or "",
        query_text=req.query_text,
        answer_excerpt=req.answer_excerpt,
        rating=req.rating,
        correction_note=req.correction_note or None,
        session_id=req.session_id,
        intent=req.intent,
        project_codes=req.project_codes,
    )
    if not feedback_id:
        raise HTTPException(status_code=503, detail="Feedback storage unavailable (run sql/144 migration).")
    return {"feedback_id": feedback_id, "status": "saved"}


@router.post("/feedback/export")
def chat_feedback_export(
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    require_role(user, ["editor", "admin"])
    from app_skeleton.api.copilot_feedback_store import export_feedback_to_eval_csv

    path = export_feedback_to_eval_csv()
    if not path:
        return {"exported": False, "message": "No feedback rows or table missing."}
    return {"exported": True, "path": str(path)}


@router.get("/status")
def chat_status(user: dict = Depends(require_platform_user)) -> dict[str, Any]:
    import os

    from app_skeleton.api.docker_service_client import docker_services

    active = _chat_llm()
    catalog = build_chat_model_catalog()
    infra = {
        "docker_local": docker_services.local_docker,
        "docker_auto_start": docker_services.auto_start_enabled,
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", ""),
        "qdrant_url": os.getenv("QDRANT_URL", ""),
        "tailscale_linux_ip": os.getenv("TAILSCALE_LINUX_IP", ""),
    }
    return {
        "chat_provider": active.provider,
        "chat_model": active.model,
        "infra": infra,
        "default_key": catalog.get("default_key"),
        "stream_enabled": os.getenv("CHAT_STREAM_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
        "max_sources": int(os.getenv("CHAT_MAX_SOURCES", "12") or "12"),
        "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "hash"),
        "embedding_model": os.getenv("TEXT_EMBEDDING_MODEL", "nomic-embed-text"),
        "rerank_enabled": os.getenv("RERANK_ENABLED", "true"),
        "session_memory": os.getenv("CHAT_SESSION_MEMORY", "true"),
        "llm": active.public_status(),
        "model_catalog": catalog,
        "agent_categories": list_visible_categories(),
        "default_agent_category": load_categories_config().get("default_category", "general_research"),
        "default_agent_mode": load_categories_config().get("default_mode", "balanced"),
    }


@router.get("/models")
def chat_models(user: dict = Depends(require_platform_user)) -> dict[str, Any]:
    return build_chat_model_catalog()


def _enforce_chat_rate_limit(request: Request, response: Response, user: dict) -> None:
    from app_skeleton.api.rate_limit import apply_rate_limit_headers, check_rate_limit

    client_ip = request.client.host if request.client else "unknown"
    allowed, headers = check_rate_limit(user_id=user.get("email"), ip_address=client_ip)
    apply_rate_limit_headers(response, headers)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")


@router.post("", response_model=ChatResponse)
def chat_message(
    req: ChatRequest,
    request: Request,
    response: Response,
    user: dict = Depends(require_platform_user),
) -> ChatResponse:
    require_role(user, ["researcher", "viewer", "editor", "admin"])
    _enforce_chat_rate_limit(request, response, user)
    active_llm = _chat_llm(req.provider, req.model)
    search_svc = _search_service(active_llm)

    result = answer_chat(
        req.message,
        project_codes=req.project_codes,
        session_id=req.session_id,
        user=user,
        llm=active_llm,
        search_svc=search_svc,
        rag_agent=rag_agent,
    )
    return ChatResponse(**_public_chat_payload(result))


def _sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
def chat_stream(
    req: ChatRequest,
    request: Request,
    response: Response,
    user: dict = Depends(require_platform_user),
) -> StreamingResponse:
    require_role(user, ["researcher", "viewer", "editor", "admin"])
    _enforce_chat_rate_limit(request, response, user)
    active_llm = _chat_llm(req.provider, req.model)
    search_svc = _search_service(active_llm)

    base = answer_chat(
        req.message,
        project_codes=req.project_codes,
        session_id=req.session_id,
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
            yield _sse_event({
                "type": "metadata",
                **{k: public_base[k] for k in ("sources", "search_hits", "limitations", "provider", "is_safe", "intent", "show_sources") if k in public_base},
                **{k: public_base[k] for k in _ORCHESTRATOR_SSE_KEYS if k in public_base},
            })
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
            **{k: public_base[k] for k in _ORCHESTRATOR_SSE_KEYS if k in public_base},
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
