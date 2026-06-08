"""Category-based multi-agent chat API."""
from __future__ import annotations

import os
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from omeia.api.agent_orchestrator.orchestrator import run_category_chat
from omeia.api.chat_service import answer_chat
from omeia.api.agent_orchestrator.rag_context import build_rag_bundle
from omeia.api.agent_orchestrator.registry import (
    get_category,
    list_visible_categories,
    public_category_detail,
)
from omeia.api.agent_orchestrator.trace_store import get_trace
from omeia.api.routers.chat import _chat_llm, _search_service
from omeia.api.common import rag_agent
from omeia.security.auth import require_platform_user
from omeia.security.permissions import require_role

router = APIRouter(tags=["agent-categories"])


class CategoryChatRequest(BaseModel):
    category: str = Field(..., description="Agent category id")
    mode: str = Field("balanced", description="fast | balanced | deep")
    message: str
    project_codes: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    library_scope: Optional[dict[str, Any]] = Field(
        None,
        description="Active document library nav scope (main_id, sub_id, filters) from the UI.",
    )
    use_rag: bool = True
    use_local_models: bool = True


@router.get("/api/agent-categories")
def agent_categories(user: dict[str, Any] = Depends(require_platform_user)) -> dict[str, Any]:
    return {
        "default_category": "general_research",
        "default_mode": "balanced",
        "categories": list_visible_categories(),
    }


@router.get("/api/agent-categories/{category_id}")
def agent_category_detail(
    category_id: str,
    mode: str = "balanced",
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    detail = public_category_detail(category_id, mode=mode)
    if not detail:
        raise HTTPException(status_code=404, detail="Unknown category")
    return detail


def _execute_category_chat(
    req: CategoryChatRequest,
    request: Request,
    response: Response,
    user: dict[str, Any],
) -> dict[str, Any]:
    from omeia.api.rate_limit import apply_rate_limit_headers, check_rate_limit

    require_role(user, ["researcher", "viewer", "editor", "admin"])
    client_ip = request.client.host if request.client else "unknown"
    allowed, headers = check_rate_limit(user_id=user.get("email"), ip_address=client_ip)
    apply_rate_limit_headers(response, headers)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    active_llm = _chat_llm(None, None)
    search_svc = _search_service(active_llm)

    def rag_fn(message, *, project_codes, user, provider, model, retrieval_only=True):
        del provider, model, retrieval_only
        scope = req.library_scope
        if scope and scope.get("main_id") and scope.get("sub_id"):
            from omeia.api.library_taxonomy import describe_nav_scope

            enriched = describe_nav_scope(scope["main_id"], scope["sub_id"])
            if enriched:
                scope = {**scope, **enriched}
        return build_rag_bundle(
            message,
            project_codes=project_codes,
            search_svc=search_svc,
            rag_agent=rag_agent,
            library_scope=scope,
            user_role=(user or {}).get("role"),
        )

    def llm_factory(provider: str | None, model: str | None):
        if req.use_local_models and not provider:
            ollama_llm = _chat_llm("ollama", model)
            if ollama_llm.healthCheck():
                return ollama_llm
        return _chat_llm(provider, model)

    use_unified = os.getenv("CATEGORY_UNIFIED_EVIDENCE", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if use_unified and req.mode in {"fast", "balanced"}:
        unified_llm = llm_factory(None, None)
        result = answer_chat(
            req.message,
            project_codes=req.project_codes,
            session_id=req.session_id,
            user=user,
            llm=unified_llm,
            search_svc=search_svc,
            rag_agent=rag_agent,
        )
        return {
            **result,
            "category": (get_category(req.category) or {}).get("label") or req.category,
            "category_id": req.category,
            "mode": req.mode,
            "execution_path": "unified_evidence",
            "execution_note": (
                "Fast/balanced mode uses the unified evidence orchestrator (single retrieval + synthesis pipeline), "
                "not the multi-agent team listed in the category preview."
            ),
            "agents_used": ["evidence_orchestrator"],
            "team_preview": (get_category(req.category) or {}).get("team_preview") or [],
            "confidence": result.get("evidence_confidence") or result.get("confidence") or "medium",
            "citations": result.get("sources") or [],
            "warnings": result.get("limitations") or [],
            "trace_id": None,
            "synthesis_mode": result.get("synthesis_mode") or "evidence_orchestrator",
            "intent": result.get("intent") or f"category_{req.category}",
        }

    deep_result = run_category_chat(
        req.message,
        category_id=req.category,
        mode=req.mode,
        project_codes=req.project_codes,
        user=user,
        llm_factory=llm_factory,
        rag_answer_fn=rag_fn,
    )
    return {
        **deep_result,
        "execution_path": "multi_agent",
        "execution_note": "Deep mode runs the configured specialist agent pipeline with synthesizer.",
    }


@router.post("/api/chat/category")
def chat_category(
    req: CategoryChatRequest,
    request: Request,
    response: Response,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    return _execute_category_chat(req, request, response, user)


@router.post("/api/agent-categories/{category_id}/run")
def run_category(
    category_id: str,
    req: CategoryChatRequest,
    request: Request,
    response: Response,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    req.category = category_id
    return _execute_category_chat(req, request, response, user)


@router.get("/api/agent-runs/{run_id}")
def get_agent_run(run_id: str, user: dict[str, Any] = Depends(require_platform_user)) -> dict[str, Any]:
    trace = get_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": run_id,
        "category": trace.get("category"),
        "mode": trace.get("mode"),
        "latency_ms": trace.get("latency_ms"),
        "agents_started": trace.get("agents_started"),
        "warnings": trace.get("warnings"),
    }


@router.get("/api/agent-runs/{run_id}/trace")
def get_agent_run_trace(
    run_id: str,
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict[str, Any]:
    require_role(user, ["admin", "editor"])
    trace = get_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Run not found")
    public = {k: v for k, v in trace.items() if not k.startswith("_")}
    return public
