"""Tests for document library bucket integration in unified search."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app_skeleton.api.search_models import SearchFilters
from app_skeleton.api.search_nav import hit_source_label, nav_for_bucket
from app_skeleton.api.search_service import (
    BUCKET_WEIGHTS,
    INTENT_SCOPES,
    SearchService,
    search_document_library,
)


class TestDocumentLibraryIntegration(unittest.TestCase):
    def test_bucket_weight_configured(self) -> None:
        self.assertEqual(BUCKET_WEIGHTS["document_library"], 0.90)

    def test_intent_scopes_include_document_library(self) -> None:
        for intent in ("research_question", "protocol_question", "search_request"):
            self.assertIn("document_library", INTENT_SCOPES[intent])

    def test_hit_source_label(self) -> None:
        self.assertEqual(hit_source_label("document_library"), "Document Library")
        self.assertEqual(hit_source_label("vault"), "Vault Asset")
        self.assertEqual(hit_source_label("lab"), "Lab Knowledge")
        self.assertEqual(hit_source_label("research"), "Research KB")

    def test_nav_for_document_library(self) -> None:
        nav = nav_for_bucket("document_library", relative_path="lab/wet_lab/protocol.pdf")
        self.assertEqual(nav.main, "document_library")
        self.assertEqual(nav.relative_path, "lab/wet_lab/protocol.pdf")

    def test_search_document_library_safe_metadata_no_original_path(self) -> None:
        rows = {
            "items": [
                {
                    "asset_id": "a1",
                    "logical_path": "lab_operations/wet_lab/protocol.pdf",
                    "filename": "protocol.pdf",
                    "display_title": "Wet Lab Protocol",
                    "processed_excerpt": "CycIF staining steps",
                    "smart_chip": "protocol",
                    "domain": "lab_operations",
                    "indexed_in_search": True,
                    "metadata_score": 72,
                    "project_hint": "SPACE",
                    "section_hint": "wet_lab_files",
                }
            ]
        }
        with patch("app_skeleton.api.search_service.search_document_library_rows", return_value=rows):
            hits = search_document_library(
                "CycIF",
                filters=SearchFilters(),
                limit=5,
                seen_paths=set(),
                seen_ids=set(),
            )
        self.assertEqual(len(hits), 1)
        hit = hits[0]
        self.assertEqual(hit.bucket, "document_library")
        self.assertEqual(hit.relative_path, "lab_operations/wet_lab/protocol.pdf")
        self.assertIsNotNone(hit.nav)
        self.assertEqual(hit.nav.main, "document_library")
        self.assertEqual(hit.nav.relative_path, "lab_operations/wet_lab/protocol.pdf")
        self.assertNotIn("original_path", hit.metadata)
        self.assertEqual(hit.metadata.get("smart_chip"), "protocol")
        self.assertEqual(hit.metadata.get("indexed_status"), "indexed")

    def test_dedup_against_existing_paths(self) -> None:
        rows = {
            "items": [
                {
                    "asset_id": "a1",
                    "logical_path": "shared/path.pdf",
                    "filename": "path.pdf",
                    "display_title": "Shared",
                }
            ]
        }
        with patch("app_skeleton.api.search_service.search_document_library_rows", return_value=rows):
            hits = search_document_library(
                "path",
                filters=SearchFilters(),
                limit=5,
                seen_paths={"shared/path.pdf"},
                seen_ids=set(),
            )
        self.assertEqual(hits, [])

    def test_unified_search_includes_document_library_scope(self) -> None:
        svc = SearchService(db_conn="postgresql://invalid:5432/nodb")
        with patch.object(svc, "_log_query"), patch(
            "app_skeleton.api.search_service.search_document_library",
            return_value=[],
        ) as mock_dl:
            svc.unified_search("protocol", scopes="document_library", limit=3)
        mock_dl.assert_called_once()


if __name__ == "__main__":
    unittest.main()
