"""Confidence scoring and storage-status rules for continuous learning."""
from __future__ import annotations

from typing import Any

from omeia.api.learning_models import FeedbackType, StorageStatus


def base_claim_confidence(
    *,
    has_citation: bool,
    claim_type: str,
    source_count: int = 0,
    feedback_signals: list[str] | None = None,
) -> float:
    """Compute 0-100 confidence from evidence and claim shape."""
    score = 35.0
    if has_citation:
        score += 25.0
    if source_count > 0:
        score += min(15.0, source_count * 5.0)
    if claim_type in ("method", "factual"):
        score += 8.0
    elif claim_type == "hypothesis":
        score -= 12.0
    elif claim_type == "interpretation":
        score -= 5.0

    signals = set(feedback_signals or [])
    if FeedbackType.THUMBS_UP.value in signals or FeedbackType.MARK_USEFUL.value in signals:
        score += 10.0
    if FeedbackType.THUMBS_DOWN.value in signals or FeedbackType.MARK_INCORRECT.value in signals:
        score -= 25.0
    if FeedbackType.NEEDS_REVIEW.value in signals:
        score -= 8.0

    return max(0.0, min(100.0, score))


def storage_status_from_confidence(
    confidence: float,
    *,
    has_citation: bool,
    feedback_signals: list[str] | None = None,
    from_pipeline: bool = False,
) -> StorageStatus:
    """Map confidence + citation rules to storage class."""
    signals = set(feedback_signals or [])

    if FeedbackType.MARK_INCORRECT.value in signals or FeedbackType.THUMBS_DOWN.value in signals:
        return StorageStatus.REJECTED

    if confidence < 50.0:
        return StorageStatus.REJECTED

    if not has_citation:
        if FeedbackType.THUMBS_UP.value in signals or FeedbackType.SAVE_TO_KNOWLEDGE_BASE.value in signals:
            return StorageStatus.DRAFT
        if confidence >= 70.0:
            return StorageStatus.LOW_CONFIDENCE
        return StorageStatus.LOW_CONFIDENCE

    if FeedbackType.THUMBS_UP.value in signals and confidence >= 70.0:
        return StorageStatus.VERIFIED

    if from_pipeline:
        if confidence >= 70.0:
            return StorageStatus.DRAFT
        if confidence >= 50.0:
            return StorageStatus.LOW_CONFIDENCE
        return StorageStatus.REJECTED

    if confidence >= 90.0:
        return StorageStatus.VERIFIED
    if confidence >= 70.0:
        return StorageStatus.DRAFT
    if confidence >= 50.0:
        return StorageStatus.LOW_CONFIDENCE
    return StorageStatus.REJECTED


def apply_feedback_adjustment(
    current_status: StorageStatus,
    confidence: float,
    *,
    has_citation: bool,
    feedback_type: str,
) -> tuple[StorageStatus, float, list[str]]:
    """Adjust status/confidence after user feedback."""
    warnings: list[str] = []
    adjusted = confidence

    if feedback_type == FeedbackType.THUMBS_UP.value:
        adjusted = min(100.0, confidence + 8.0)
        if not has_citation:
            warnings.append("Thumbs up without citation — user-approved note, not verified scientific fact.")
            return StorageStatus.DRAFT, adjusted, warnings
        if adjusted >= 70.0:
            return StorageStatus.VERIFIED, adjusted, warnings
    elif feedback_type == FeedbackType.MARK_USEFUL.value:
        adjusted = min(100.0, confidence + 5.0)
    elif feedback_type == FeedbackType.THUMBS_DOWN.value:
        adjusted = max(0.0, confidence - 20.0)
        return StorageStatus.REJECTED, adjusted, warnings
    elif feedback_type == FeedbackType.MARK_INCORRECT.value:
        adjusted = max(0.0, confidence - 35.0)
        return StorageStatus.REJECTED, adjusted, warnings
    elif feedback_type == FeedbackType.NEEDS_REVIEW.value:
        adjusted = max(0.0, confidence - 5.0)
        if current_status == StorageStatus.VERIFIED:
            return StorageStatus.DRAFT, adjusted, warnings
        return StorageStatus.LOW_CONFIDENCE, adjusted, warnings
    elif feedback_type == FeedbackType.SAVE_TO_KNOWLEDGE_BASE.value:
        adjusted = min(100.0, confidence + 12.0)
        if not has_citation:
            warnings.append("Saved to knowledge base without citation — stored as draft for review.")
            return StorageStatus.DRAFT, adjusted, warnings

    new_status = storage_status_from_confidence(
        adjusted,
        has_citation=has_citation,
        feedback_signals=[feedback_type],
    )
    return new_status, adjusted, warnings


def retrieval_warning_for_status(status: StorageStatus) -> str | None:
    if status == StorageStatus.DRAFT:
        return "Draft lab knowledge — review before treating as fact."
    if status == StorageStatus.LOW_CONFIDENCE:
        return "Low-confidence knowledge — use with caution."
    if status == StorageStatus.DEPRECATED:
        return "Deprecated knowledge — superseded by a newer version."
    return None


def score_knowledge_for_retrieval(item: dict[str, Any]) -> float:
    """Rank verified lab knowledge above drafts; never rank rejected."""
    status = (item.get("storage_status") or "").upper()
    if status == StorageStatus.REJECTED.value:
        return -1.0
    base = float(item.get("confidence_score") or 0.0) / 100.0
    boosts = {
        StorageStatus.VERIFIED.value: 1.0,
        StorageStatus.DRAFT.value: 0.55,
        StorageStatus.LOW_CONFIDENCE.value: 0.35,
        StorageStatus.DEPRECATED.value: 0.1,
    }
    return base + boosts.get(status, 0.2)
