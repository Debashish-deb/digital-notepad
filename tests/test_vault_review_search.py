"""Tests for vault review bucket — safe metadata only, suggestions not actions."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from omeia.api.search_models import SearchFilters
from omeia.api.search_service import search_vault_review


class TestVaultReviewSearch(unittest.TestCase):
    def _sample_row(self) -> dict:
        return {
            "asset_id": "vault-1",
            "logical_path": "lab_operations/overview/doc.pdf",
            "filename": "doc.pdf",
            "assignment_confidence": 0.42,
            "review_status": "tentative",
            "extraction_status": "ok",
            "vector_status": "pending",
            "project_hint": "SPACE",
            "section_hint": "overview_documents",
            "indexed_at": None,
        }

    def test_no_original_path_in_hits(self) -> None:
        with patch("omeia.api.search_service.review_queue", return_value=[self._sample_row()]):
            hits = search_vault_review("doc", filters=SearchFilters(), limit=5)
        self.assertGreaterEqual(len(hits), 1)
        payload = json.dumps([h.model_dump() for h in hits])
        self.assertNotIn("original_path", payload)

    def test_suggestions_only_metadata(self) -> None:
        with patch("omeia.api.search_service.review_queue", return_value=[self._sample_row()]):
            hits = search_vault_review("doc", filters=SearchFilters(), limit=5)
        hit = hits[0]
        self.assertEqual(hit.metadata.get("action"), "review_suggested")
        self.assertIn("suggestion", hit.metadata)
        self.assertIn(hit.metadata.get("review_reason"), {
            "low_confidence", "uncategorized", "failed_extraction", "not_indexed", "duplicate",
        })

    def test_duplicate_candidates_use_logical_paths_only(self) -> None:
        dup_report = {
            "groups": [
                {
                    "checksum_sha256": "abc123",
                    "count": 2,
                    "logical_paths": ["a/file.pdf", "b/file.pdf"],
                }
            ]
        }
        with patch("omeia.api.search_service.review_queue", return_value=[]), patch(
            "omeia.api.search_service.deduplication_report",
            return_value=dup_report,
        ):
            hits = search_vault_review("file", filters=SearchFilters(), limit=5)
        dup_hits = [h for h in hits if h.metadata.get("review_reason") == "duplicate"]
        self.assertEqual(len(dup_hits), 1)
        self.assertEqual(dup_hits[0].metadata.get("logical_paths"), ["a/file.pdf", "b/file.pdf"])
        self.assertNotIn("delete", dup_hits[0].snippet.lower())
        self.assertNotIn("move", dup_hits[0].snippet.lower())


if __name__ == "__main__":
    unittest.main()
