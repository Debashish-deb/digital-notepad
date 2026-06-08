"""Tests for advanced unified search filters and unsupported_filters reporting."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app_skeleton.api.search_models import SearchFilters
from app_skeleton.api.search_service import (
    FILTER_SOURCE_SUPPORT,
    SearchService,
    _build_search_filters,
    _resolve_filter_metadata,
)


class TestAdvancedFilters(unittest.TestCase):
    def test_build_search_filters_merges_section_id(self) -> None:
        filters = _build_search_filters(section_id="wet_lab_files", smart_chip="protocol")
        self.assertEqual(filters.section_id, "wet_lab_files")
        self.assertEqual(filters.smart_chip, "protocol")

    def test_unsupported_filters_for_lab_only_scope(self) -> None:
        filters = SearchFilters(smart_chip="protocol", category="sop", section_id="wet_lab_files")
        applied, unsupported = _resolve_filter_metadata({"lab", "file"}, filters)
        self.assertIn("smart_chip", unsupported)
        self.assertIn("category", unsupported)
        self.assertIn("section_id", applied)

    def test_document_library_supports_smart_chip(self) -> None:
        filters = SearchFilters(smart_chip="protocol", category="sop")
        applied, unsupported = _resolve_filter_metadata({"document_library"}, filters)
        self.assertNotIn("smart_chip", unsupported)
        self.assertNotIn("category", unsupported)
        self.assertIn("smart_chip", applied)

    def test_source_buckets_alias_in_active_fields(self) -> None:
        filters = SearchFilters(source_buckets="lab,document_library")
        active = filters.active_fields()
        self.assertEqual(active.get("source_buckets"), "lab,document_library")

    def test_unified_search_reports_unsupported_filters(self) -> None:
        svc = SearchService(db_conn="postgresql://invalid:5432/nodb")
        with patch.object(svc, "_log_query"):
            resp = svc.unified_search(
                "Ashlar protocol",
                scopes="lab",
                smart_chip="wet_lab",
                category="protocol",
                limit=5,
            )
        self.assertIn("smart_chip", resp.unsupported_filters)
        self.assertIn("category", resp.unsupported_filters)

    def test_backward_compatible_without_filters(self) -> None:
        svc = SearchService(db_conn="postgresql://invalid:5432/nodb")
        with patch.object(svc, "_log_query"):
            resp = svc.unified_search("Ashlar stitching", limit=5)
        self.assertEqual(resp.unsupported_filters, [])
        self.assertEqual(resp.filters_applied, {})

    def test_filter_source_support_covers_advanced_fields(self) -> None:
        dl_support = FILTER_SOURCE_SUPPORT["document_library"]
        self.assertIn("smart_chip", dl_support)
        self.assertIn("date_from", dl_support)
        self.assertIn("indexed_status", dl_support)


if __name__ == "__main__":
    unittest.main()
