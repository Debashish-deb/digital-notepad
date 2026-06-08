"""Verified knowledge policy — pipeline vs user approval."""
from __future__ import annotations

import unittest

from omeia.api.confidence_scorer import storage_status_from_confidence
from omeia.api.learning_models import FeedbackType, StorageStatus


class TestVerifiedKnowledgePolicy(unittest.TestCase):
    def test_pipeline_never_auto_verifies(self) -> None:
        status = storage_status_from_confidence(95.0, has_citation=True, from_pipeline=True)
        self.assertEqual(status, StorageStatus.DRAFT)

    def test_low_confidence_pipeline_rejected(self) -> None:
        status = storage_status_from_confidence(45.0, has_citation=False, from_pipeline=True)
        self.assertEqual(status, StorageStatus.REJECTED)

    def test_thumbs_up_with_citation_can_verify(self) -> None:
        status = storage_status_from_confidence(
            75.0,
            has_citation=True,
            feedback_signals=[FeedbackType.THUMBS_UP.value],
        )
        self.assertEqual(status, StorageStatus.VERIFIED)


if __name__ == "__main__":
    unittest.main()
