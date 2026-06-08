"""Teacher-Student continuous learning API."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from omeia.api.learning_models import (
    FeedbackRequest,
    KnowledgeReviewRequest,
    RecordResponseRequest,
)
from omeia.api.learning_pipeline_service import (
    apply_user_feedback,
    record_and_run_pipeline,
    review_knowledge_item,
)
from omeia.api.learning_store import list_graph_edges, schema_available, search_knowledge
from omeia.api.platform_flags import continuous_learning_enabled
from omeia.security.auth import require_platform_user
from omeia.security.permissions import require_role

LOGGER = logging.getLogger(__name__)
router = APIRouter(tags=["learning"])


def _require_learning_enabled() -> None:
    if not continuous_learning_enabled():
        raise HTTPException(status_code=503, detail="Continuous learning is disabled (OMEIA_CONTINUOUS_LEARNING_ENABLED=false).")


@router.get("/api/learning/status")
def learning_status(user: dict = Depends(require_platform_user)) -> dict[str, Any]:
    require_role(user, ["researcher", "viewer", "editor", "admin"])
    return {
        "enabled": continuous_learning_enabled(),
        "schema_available": schema_available(),
    }


@router.post("/api/learning/responses")
def record_learning_response(
    req: RecordResponseRequest,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    """Record expert/teacher answer and run learning pipeline."""
    require_role(user, ["researcher", "editor", "admin"])
    _require_learning_enabled()
    if not schema_available():
        raise HTTPException(status_code=503, detail="Run sql/150_continuous_learning.sql migration first.")

    result = record_and_run_pipeline(req, user_email=user.get("email"))
    if not result:
        raise HTTPException(status_code=500, detail="Failed to record AI response.")
    return result.model_dump(mode="json")


@router.post("/api/learning/feedback")
def learning_feedback(
    req: FeedbackRequest,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    """Thumbs, useful/incorrect, needs review, save to knowledge base."""
    require_role(user, ["researcher", "viewer", "editor", "admin"])
    _require_learning_enabled()
    if not schema_available():
        raise HTTPException(status_code=503, detail="Learning schema unavailable.")

    outcome = apply_user_feedback(
        response_id=str(req.response_id),
        user_email=user.get("email") or "",
        feedback_type=req.feedback_type.value,
        rating=req.rating,
        comment=req.comment,
    )
    if not outcome.get("feedback_id"):
        raise HTTPException(status_code=500, detail="Feedback save failed.")
    return outcome


@router.get("/api/learning/knowledge")
def list_knowledge(
    q: str = Query("", min_length=0),
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    require_role(user, ["researcher", "viewer", "editor", "admin"])
    _require_learning_enabled()
    status_filter = [status.upper()] if status else None
    items = search_knowledge(q or " ", status_filter=status_filter, limit=limit)
    return {"query": q, "count": len(items), "items": items}


@router.get("/api/learning/graph/edges")
def graph_edges(
    subject: str | None = Query(None),
    object_name: str | None = Query(None, alias="object"),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    require_role(user, ["researcher", "viewer", "editor", "admin"])
    _require_learning_enabled()
    edges = list_graph_edges(subject_name=subject, object_name=object_name, limit=limit)
    return {"count": len(edges), "edges": edges}


@router.post("/api/learning/knowledge/{knowledge_id}/review")
def knowledge_review(
    knowledge_id: UUID,
    req: KnowledgeReviewRequest,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    require_role(user, ["editor", "admin"])
    _require_learning_enabled()
    return review_knowledge_item(str(knowledge_id), action=req.action.value, comment=req.comment)


class ThreadCreateRequest(BaseModel):
    title: str
    hypothesis: str | None = None
    initial_query: str | None = None
    initial_answer: str | None = None
    response_id: str | None = None


class ThreadChallengeRequest(BaseModel):
    challenge_text: str
    project_codes: list[str] = Field(default_factory=list)
    agent_category: str | None = None


@router.post("/api/learning/threads")
def create_learning_thread(
    req: ThreadCreateRequest,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    from omeia.api.lab_knowledge_threads import create_thread
    from omeia.api.platform_flags import lab_knowledge_threads_enabled

    require_role(user, ["researcher", "viewer", "editor", "admin"])
    if not lab_knowledge_threads_enabled():
        raise HTTPException(status_code=503, detail="Lab Knowledge Threads disabled (OMEIA_LAB_KNOWLEDGE_THREADS=false).")
    return create_thread(
        title=req.title,
        hypothesis=req.hypothesis,
        user_email=user.get("email") or "",
        initial_query=req.initial_query,
        initial_answer=req.initial_answer,
        response_id=req.response_id,
    )


@router.get("/api/learning/threads/{thread_id}")
def get_learning_thread(thread_id: str, user: dict = Depends(require_platform_user)) -> dict[str, Any]:
    from omeia.api.lab_knowledge_threads import get_thread

    require_role(user, ["researcher", "viewer", "editor", "admin"])
    thread = get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.post("/api/learning/threads/{thread_id}/challenge")
def challenge_learning_thread(
    thread_id: str,
    req: ThreadChallengeRequest,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    from omeia.api.common import rag_agent
    from omeia.api.lab_knowledge_threads import challenge_thread
    from omeia.api.platform_flags import lab_knowledge_threads_enabled
    from omeia.api.routers.chat import _chat_llm, _search_service

    require_role(user, ["researcher", "editor", "admin"])
    if not lab_knowledge_threads_enabled():
        raise HTTPException(status_code=503, detail="Lab Knowledge Threads disabled.")
    active_llm = _chat_llm(None, None)
    search_svc = _search_service(active_llm)
    outcome = challenge_thread(
        thread_id=thread_id,
        challenge_text=req.challenge_text,
        user_email=user.get("email") or "",
        user=user,
        llm=active_llm,
        search_svc=search_svc,
        rag_agent=rag_agent,
        project_codes=req.project_codes,
        agent_category=req.agent_category,
    )
    if not outcome.get("ok"):
        raise HTTPException(status_code=503, detail=outcome.get("error", "challenge_failed"))
    return outcome


class ProjectBriefRequest(BaseModel):
    project_code: str
    focus_question: str = ""


@router.post("/api/learning/project-briefs")
def generate_project_brief(
    req: ProjectBriefRequest,
    user: dict = Depends(require_platform_user),
) -> dict[str, Any]:
    from omeia.api.project_intelligence_briefs import generate_project_brief as _generate
    from omeia.api.platform_flags import project_intelligence_briefs_enabled
    from omeia.api.routers.chat import _chat_llm, _search_service

    require_role(user, ["researcher", "editor", "admin"])
    if not project_intelligence_briefs_enabled():
        raise HTTPException(status_code=503, detail="Project Intelligence Briefs disabled.")
    active_llm = _chat_llm(None, None)
    search_svc = _search_service(active_llm)
    return _generate(
        project_code=req.project_code,
        focus_question=req.focus_question,
        search_svc=search_svc,
        llm=active_llm,
        user_role=user.get("role"),
    )
