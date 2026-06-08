"""Feedback adjustment and platform flag tests."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from omeia.api.confidence_scorer import apply_feedback_adjustment
from omeia.api.learning_models import FeedbackType, StorageStatus
from omeia.api.learning_pipeline_service import apply_user_feedback
from omeia.api.platform_flags import continuous_learning_enabled


def test_continuous_learning_flag_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMEIA_CONTINUOUS_LEARNING_ENABLED", raising=False)
    assert continuous_learning_enabled() is False


def test_continuous_learning_flag_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMEIA_CONTINUOUS_LEARNING_ENABLED", "true")
    assert continuous_learning_enabled() is True


def test_save_to_kb_without_citation_warning() -> None:
    status, _, warnings = apply_feedback_adjustment(
        StorageStatus.DRAFT,
        60.0,
        has_citation=False,
        feedback_type=FeedbackType.SAVE_TO_KNOWLEDGE_BASE.value,
    )
    assert status == StorageStatus.DRAFT
    assert warnings


@patch("omeia.api.learning_pipeline_service.insert_feedback")
@patch("omeia.api.learning_pipeline_service.get_response")
@patch("omeia.api.learning_pipeline_service.search_knowledge")
def test_apply_user_feedback_persists(
    mock_search,
    mock_get_response,
    mock_insert_feedback,
) -> None:
    mock_insert_feedback.return_value = "fb-1"
    mock_get_response.return_value = {
        "answer_text": "TLS is important in HGSC.",
        "has_citations": False,
    }
    mock_search.return_value = [{
        "knowledge_id": "k-1",
        "response_id": "r-1",
        "storage_status": "DRAFT",
        "confidence_score": 65.0,
        "has_citation": False,
    }]

    with patch("omeia.api.learning_pipeline_service.update_knowledge_status") as mock_update:
        outcome = apply_user_feedback(
            response_id="r-1",
            user_email="test@example.com",
            feedback_type=FeedbackType.THUMBS_UP.value,
            rating=1,
        )

    assert outcome["feedback_id"] == "fb-1"
    assert outcome["status"] == "saved"
    mock_update.assert_called_once()
