"""Orchestrates Teacher-Student continuous learning pipeline."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from omeia.api.claim_extractor import extract_claims_rule_based
from omeia.api.confidence_scorer import (
    apply_feedback_adjustment,
    base_claim_confidence,
    storage_status_from_confidence,
)
from omeia.api.contradiction_checker import detect_contradictions, resolve_contradiction_status
from omeia.api.knowledge_graph_service import extract_graph_from_text
from omeia.api.learning_models import (
    FeedbackType,
    PipelineResult,
    PipelineStatus,
    RecordResponseRequest,
    ReviewAction,
    StorageStatus,
)
from omeia.api.learning_store import (
    get_knowledge_item,
    get_response,
    insert_ai_response,
    insert_claim,
    insert_evidence,
    insert_feedback,
    insert_knowledge_item,
    list_feedback_for_response,
    schema_available,
    search_knowledge,
    update_knowledge_status,
    update_pipeline_status,
)

LOGGER = logging.getLogger(__name__)


def _sources_from_payload(sources: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for src in sources or []:
        if isinstance(src, dict):
            out.append(src)
        elif hasattr(src, "model_dump"):
            out.append(src.model_dump())
    return out


def record_and_run_pipeline(
    req: RecordResponseRequest,
    *,
    user_email: str | None = None,
) -> PipelineResult | None:
    """Record expert/student answer and run full learning pipeline."""
    if not schema_available():
        LOGGER.debug("Continuous learning schema unavailable — skipping pipeline")
        return None

    sources = _sources_from_payload([s.model_dump() if hasattr(s, "model_dump") else s for s in req.sources])
    citation_count = len(sources)
    has_citations = citation_count > 0 or any(s.get("chunk_id") or s.get("doi") for s in sources)

    response_id = insert_ai_response(
        query_text=req.query_text,
        answer_text=req.answer_text,
        user_email=user_email,
        session_id=req.session_id,
        model_provider=req.model_provider,
        model_name=req.model_name,
        model_role=req.model_role.value if hasattr(req.model_role, "value") else str(req.model_role),
        intent=req.intent,
        project_codes=req.project_codes,
        source_ids=sources,
        citation_count=citation_count,
        has_citations=has_citations,
        metadata=req.metadata,
    )
    if not response_id:
        return None

    if not req.run_pipeline:
        update_pipeline_status(response_id, PipelineStatus.SKIPPED.value)
        return PipelineResult(
            response_id=UUID(response_id),
            pipeline_status=PipelineStatus.SKIPPED,
        )

    return run_pipeline_for_response(response_id, sources=sources)


def run_pipeline_for_response(
    response_id: str,
    *,
    sources: list[dict[str, Any]] | None = None,
) -> PipelineResult:
    """Execute: claim → source → confidence → contradiction → classify → store → graph."""
    warnings: list[str] = []
    update_pipeline_status(response_id, PipelineStatus.PROCESSING.value)

    row = get_response(response_id)
    if not row:
        update_pipeline_status(response_id, PipelineStatus.FAILED.value)
        return PipelineResult(
            response_id=UUID(response_id),
            pipeline_status=PipelineStatus.FAILED,
            warnings=["Response record not found"],
        )

    answer_text = row.get("answer_text") or ""
    sources = sources or []
    if not sources and row.get("metadata"):
        meta = row["metadata"]
        if isinstance(meta, dict):
            sources = meta.get("sources") or []

    claims_raw = extract_claims_rule_based(answer_text, sources=sources)
    claim_records: list[dict[str, Any]] = []
    knowledge_records: list[dict[str, Any]] = []
    graph_records: list[dict[str, Any]] = []
    all_contradictions: list[dict[str, Any]] = []

    existing_knowledge = search_knowledge(answer_text[:200], limit=30)

    for claim in claims_raw:
        confidence = base_claim_confidence(
            has_citation=bool(claim.get("has_citation")),
            claim_type=claim.get("claim_type", "factual"),
            source_count=len(sources),
        )
        status = storage_status_from_confidence(
            confidence,
            has_citation=bool(claim.get("has_citation")),
        )

        claim_id = insert_claim(
            response_id=response_id,
            claim_text=claim["claim_text"],
            claim_type=claim.get("claim_type", "factual"),
            confidence_score=confidence,
            has_citation=bool(claim.get("has_citation")),
            extraction_method=claim.get("extraction_method", "rule_based"),
            metadata=claim.get("metadata"),
        )
        if not claim_id:
            continue

        claim_records.append({
            "claim_id": claim_id,
            "claim_text": claim["claim_text"],
            "confidence_score": confidence,
            "has_citation": claim.get("has_citation"),
        })

        for src in sources[:5]:
            insert_evidence(
                response_id=response_id,
                claim_id=claim_id,
                source_type=src.get("source_type") or "citation",
                title=src.get("title"),
                url=src.get("url"),
                doi=src.get("doi"),
                pmid=src.get("pmid"),
                accession=src.get("accession"),
                chunk_id=src.get("chunk_id"),
                source_uuid=src.get("source_uuid"),
                excerpt=src.get("text_preview") or src.get("excerpt"),
                confidence_score=confidence,
            )

        contradictions = detect_contradictions(claim["claim_text"], existing_knowledge)
        contradiction_flags: list[str] = []
        for conflict in contradictions:
            all_contradictions.append(conflict)
            contradiction_flags.append(conflict.get("reason", "conflict"))
            existing_id = conflict.get("knowledge_id")
            existing = next((k for k in existing_knowledge if str(k.get("knowledge_id")) == existing_id), None)
            if existing:
                action, _ = resolve_contradiction_status(
                    confidence,
                    float(existing.get("confidence_score") or 0),
                    existing.get("storage_status") or "",
                )
                if action == "deprecate_existing" and existing_id:
                    update_knowledge_status(existing_id, StorageStatus.DEPRECATED.value, deprecate=True)
                    warnings.append(f"Deprecated weaker knowledge {existing_id} due to contradiction.")

        if status == StorageStatus.REJECTED.value and confidence < 50:
            warnings.append(f"Claim archived only (confidence {confidence:.0f}%): {claim['claim_text'][:80]}")
            continue

        title = claim["claim_text"][:120]
        knowledge_id = insert_knowledge_item(
            response_id=response_id,
            claim_id=claim_id,
            title=title,
            content=claim["claim_text"],
            storage_status=status.value if hasattr(status, "value") else str(status),
            confidence_score=confidence,
            has_citation=bool(claim.get("has_citation")),
            classification=claim.get("claim_type"),
            contradiction_flags=contradiction_flags,
            metadata={"pipeline": "continuous_learning"},
        )
        if knowledge_id:
            knowledge_records.append({
                "knowledge_id": knowledge_id,
                "title": title,
                "storage_status": status.value if hasattr(status, "value") else str(status),
                "confidence_score": confidence,
            })
            edges = extract_graph_from_text(
                claim["claim_text"],
                knowledge_id=knowledge_id,
                storage_status=status.value if hasattr(status, "value") else str(status),
                confidence_score=confidence,
            )
            graph_records.extend(edges)

    update_pipeline_status(response_id, PipelineStatus.COMPLETED.value)

    from omeia.api.learning_models import ExtractedClaimRecord, GraphEdgeRecord, KnowledgeItemRecord

    return PipelineResult(
        response_id=UUID(response_id),
        pipeline_status=PipelineStatus.COMPLETED,
        claims=[
            ExtractedClaimRecord(
                claim_id=UUID(c["claim_id"]),
                response_id=UUID(response_id),
                claim_text=c["claim_text"],
                confidence_score=c["confidence_score"],
                has_citation=c.get("has_citation", False),
            )
            for c in claim_records
        ],
        knowledge_items=[
            KnowledgeItemRecord(
                knowledge_id=UUID(k["knowledge_id"]),
                response_id=UUID(response_id),
                title=k["title"],
                content=k["title"],
                storage_status=StorageStatus(k["storage_status"]),
                confidence_score=k["confidence_score"],
            )
            for k in knowledge_records
        ],
        graph_edges=[
            GraphEdgeRecord(
                edge_id=UUID(e["edge_id"]),
                subject_name=e["subject_name"],
                subject_type=e["subject_type"],
                relation_type=e["relation_type"],
                object_name=e["object_name"],
                object_type=e["object_type"],
                confidence_score=float(e.get("confidence_score") or 0.0),
                storage_status=StorageStatus(e.get("storage_status", StorageStatus.DRAFT.value)),
            )
            for e in graph_records
            if e.get("edge_id")
        ],
        contradictions=all_contradictions,
        warnings=warnings,
    )


def record_chat_response(
    *,
    query_text: str,
    answer_text: str,
    user_email: str | None,
    session_id: str | None,
    model_provider: str | None,
    model_name: str | None,
    intent: str | None,
    project_codes: list[str] | None,
    sources: list[dict[str, Any]] | None,
) -> str | None:
    """Lightweight hook from chat_service — record student response + pipeline."""
    req = RecordResponseRequest(
        query_text=query_text,
        answer_text=answer_text,
        session_id=session_id,
        model_provider=model_provider,
        model_name=model_name,
        intent=intent,
        project_codes=project_codes or [],
        sources=[
            {
                "title": s.get("title"),
                "source_type": s.get("source_type"),
                "source_uuid": s.get("source_uuid"),
                "chunk_id": s.get("chunk_id"),
                "excerpt": s.get("text_preview"),
            }
            for s in (sources or [])
        ],
        run_pipeline=True,
        metadata={"origin": "chat_service"},
    )
    result = record_and_run_pipeline(req, user_email=user_email)
    return str(result.response_id) if result else None


def apply_user_feedback(
    *,
    response_id: str,
    user_email: str,
    feedback_type: str,
    rating: int | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    """Process feedback and re-score linked knowledge items."""
    feedback_id = insert_feedback(
        response_id=response_id,
        user_email=user_email,
        feedback_type=feedback_type,
        rating=rating,
        comment=comment,
    )
    if not feedback_id:
        return {"feedback_id": None, "status": "failed"}

    row = get_response(response_id)
    warnings: list[str] = []
    updated_items: list[str] = []

    if row:
        items = search_knowledge((row.get("answer_text") or "")[:200], limit=10)
        for item in items:
            if str(item.get("response_id")) != response_id:
                continue
            current_status = StorageStatus(item.get("storage_status") or StorageStatus.DRAFT.value)
            new_status, new_conf, item_warnings = apply_feedback_adjustment(
                current_status,
                float(item.get("confidence_score") or 0),
                has_citation=bool(item.get("has_citation")),
                feedback_type=feedback_type,
            )
            update_knowledge_status(
                str(item["knowledge_id"]),
                new_status.value,
                confidence_score=new_conf,
            )
            updated_items.append(str(item["knowledge_id"]))
            warnings.extend(item_warnings)

    if feedback_type == FeedbackType.SAVE_TO_KNOWLEDGE_BASE.value and not updated_items and row:
        kid = insert_knowledge_item(
            response_id=response_id,
            claim_id=None,
            title=(row.get("query_text") or "User-saved knowledge")[:120],
            content=row.get("answer_text") or "",
            storage_status=StorageStatus.DRAFT.value,
            confidence_score=65.0,
            has_citation=bool(row.get("has_citations")),
            metadata={"saved_by_feedback": True},
        )
        if kid:
            updated_items.append(kid)
            if not row.get("has_citations"):
                warnings.append("Saved without citation — draft for review, not verified fact.")

    return {
        "feedback_id": feedback_id,
        "status": "saved",
        "updated_knowledge_ids": updated_items,
        "warnings": warnings,
    }


def review_knowledge_item(
    knowledge_id: str,
    *,
    action: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Approve, reject, or deprecate a knowledge item."""
    item = get_knowledge_item(knowledge_id)
    if not item:
        return {"ok": False, "error": "not_found"}

    if action == ReviewAction.APPROVE.value:
        if not item.get("has_citation"):
            update_knowledge_status(knowledge_id, StorageStatus.DRAFT.value)
            return {
                "ok": True,
                "knowledge_id": knowledge_id,
                "storage_status": StorageStatus.DRAFT.value,
                "warning": "Cannot verify without citation — kept as draft.",
            }
        update_knowledge_status(knowledge_id, StorageStatus.VERIFIED.value, confidence_score=92.0)
        return {"ok": True, "knowledge_id": knowledge_id, "storage_status": StorageStatus.VERIFIED.value}

    if action == ReviewAction.REJECT.value:
        update_knowledge_status(knowledge_id, StorageStatus.REJECTED.value)
        return {"ok": True, "knowledge_id": knowledge_id, "storage_status": StorageStatus.REJECTED.value}

    if action == ReviewAction.DEPRECATE.value:
        update_knowledge_status(knowledge_id, StorageStatus.DEPRECATED.value, deprecate=True)
        return {"ok": True, "knowledge_id": knowledge_id, "storage_status": StorageStatus.DEPRECATED.value}

    return {"ok": False, "error": "invalid_action", "comment": comment}
