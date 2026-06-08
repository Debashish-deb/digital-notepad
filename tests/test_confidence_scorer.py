"""Confidence scoring rules for continuous learning."""
from __future__ import annotations

from omeia.api.confidence_scorer import (
    apply_feedback_adjustment,
    base_claim_confidence,
    score_knowledge_for_retrieval,
    storage_status_from_confidence,
)
from omeia.api.learning_models import FeedbackType, StorageStatus


def test_verified_requires_citation_and_high_confidence() -> None:
    status = storage_status_from_confidence(95.0, has_citation=True)
    assert status == StorageStatus.VERIFIED


def test_no_citation_never_verified() -> None:
    status = storage_status_from_confidence(95.0, has_citation=False)
    assert status != StorageStatus.VERIFIED


def test_low_confidence_archived_only() -> None:
    status = storage_status_from_confidence(40.0, has_citation=True)
    assert status == StorageStatus.REJECTED


def test_draft_band_with_citation() -> None:
    status = storage_status_from_confidence(75.0, has_citation=True)
    assert status == StorageStatus.DRAFT


def test_thumbs_up_without_citation_is_draft_not_verified() -> None:
    status, conf, warnings = apply_feedback_adjustment(
        StorageStatus.LOW_CONFIDENCE,
        72.0,
        has_citation=False,
        feedback_type=FeedbackType.THUMBS_UP.value,
    )
    assert status == StorageStatus.DRAFT
    assert conf > 72.0
    assert any("not verified" in w.lower() or "user-approved" in w.lower() for w in warnings)


def test_mark_incorrect_rejects() -> None:
    status, conf, _ = apply_feedback_adjustment(
        StorageStatus.DRAFT,
        80.0,
        has_citation=True,
        feedback_type=FeedbackType.MARK_INCORRECT.value,
    )
    assert status == StorageStatus.REJECTED
    assert conf < 80.0


def test_retrieval_ranking_prefers_verified() -> None:
    verified = score_knowledge_for_retrieval({
        "storage_status": "VERIFIED",
        "confidence_score": 80.0,
    })
    draft = score_knowledge_for_retrieval({
        "storage_status": "DRAFT",
        "confidence_score": 80.0,
    })
    rejected = score_knowledge_for_retrieval({
        "storage_status": "REJECTED",
        "confidence_score": 99.0,
    })
    assert verified > draft
    assert rejected < 0


def test_base_claim_confidence_boosts_citation() -> None:
    with_cite = base_claim_confidence(has_citation=True, claim_type="factual", source_count=2)
    without = base_claim_confidence(has_citation=False, claim_type="factual", source_count=0)
    assert with_cite > without
