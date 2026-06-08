"""Teacher-Student continuous learning API."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

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
