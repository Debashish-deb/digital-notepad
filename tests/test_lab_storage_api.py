"""Unit tests for Phase 1 storage roots and lab API path hygiene."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app_skeleton.api import lab_knowledge_store as lks
from app_skeleton.api.database_sections import list_sections, assert_all_section_roots_exist
from app_skeleton.api.raw_vault_store import search_vault, _public_row, deduplication_report
from app_skeleton.api.main import app
from app_skeleton.api.paths import storage_roots_public_summary


class TestStorageRoots(unittest.TestCase):
    def test_public_summary_has_no_absolute_paths(self):
        rows = storage_roots_public_summary()
        self.assertGreaterEqual(len(rows), 4)
        for row in rows:
            self.assertIn("id", row)
            self.assertIn("configured", row)
            for key, val in row.items():
                if isinstance(val, str):
                    self.assertNotIn("/Users/", val)
                    self.assertNotIn("\\\\", val)

    def test_list_sections_no_absolute_root(self):
        for section in list_sections():
            self.assertIn("logical_root", section)
            self.assertNotIn("absolute_root", section)


class TestLabSearchHitFormat(unittest.TestCase):
    def test_format_search_hit_omits_disk_paths(self):
        hit = lks._format_search_hit(
            1,
            0.9,
            {
                "section_id": "wet_lab_files",
                "section_label": "Wet-lab files",
                "relative_path": "WET_LAB/protocols/foo.md",
                "title": "foo.md",
                "text_preview": "lab coats required",
                "absolute_disk_path": "/secret/path/WET_LAB/protocols/foo.md",
                "database_root": "/secret/database",
            },
            "chunk-1",
        )
        blob = str(hit)
        self.assertNotIn("/secret/", blob)
        self.assertIn("where_to_find", hit)
        self.assertEqual(hit["relative_path"], "WET_LAB/protocols/foo.md")


class TestSectionRoots(unittest.TestCase):
    def test_all_configured_section_roots_exist(self):
        missing = assert_all_section_roots_exist()
        self.assertEqual(missing, [], f"Missing section folders: {missing}")


class TestDedupeReport(unittest.TestCase):
    def test_dedupe_report_structure(self):
        report = deduplication_report(limit=5)
        self.assertIn("duplicate_checksum_groups", report)
        self.assertIn("groups", report)
        for group in report["groups"]:
            self.assertNotIn("original_path", str(group))


class TestRawVault(unittest.TestCase):
    def test_public_row_strips_original_path(self):
        row = _public_row({
            "asset_id": "asset_x",
            "original_path": "/secret/abs/path.pdf",
            "logical_path": "WET_LAB/x.pdf",
            "filename": "x.pdf",
            "storage_provider": "local_database_mirror",
            "assignment_confidence": 0.5,
            "review_status": "raw",
        })
        self.assertNotIn("original_path", row)
        self.assertEqual(row["logical_path"], "WET_LAB/x.pdf")

    def test_search_vault_finds_token(self):
        hits = search_vault("protocol", limit=5)
        if hits:
            self.assertIn("logical_path", hits[0])


class TestLabApiEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_storage_roots_endpoint(self):
        res = self.client.get("/api/storage/roots")
        self.assertEqual(res.status_code, 200)
        providers = res.json().get("providers") or []
        self.assertTrue(any(p["id"] == "local_database_mirror" for p in providers))

    def test_database_sections_no_database_root_key(self):
        res = self.client.get("/api/database/sections")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertNotIn("database_root", body)

    def test_database_tree_deprecated(self):
        res = self.client.get(
            "/api/database/tree",
            params={"section_id": "overview_personnel"},
        )
        self.assertEqual(res.status_code, 410)

    def test_database_read_deprecated(self):
        res = self.client.get(
            "/api/database/read",
            params={"section_id": "overview_personnel", "relative_path": "x.txt"},
        )
        self.assertEqual(res.status_code, 410)

    def test_database_extract_deprecated(self):
        res = self.client.get(
            "/api/database/extract",
            params={"section_id": "wet_lab_files", "relative_path": "x.pdf"},
        )
        self.assertEqual(res.status_code, 410)

    def test_vault_summary_endpoint(self):
        res = self.client.get("/api/vault/summary")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertNotIn("database_root", body.get("summary") or {})

    def test_vault_search_endpoint(self):
        res = self.client.get("/api/vault/search", params={"q": "lab", "limit": 3})
        self.assertEqual(res.status_code, 200)

    def test_vault_dedupe_endpoint(self):
        res = self.client.get("/api/vault/dedupe-report", params={"limit": 5})
        self.assertEqual(res.status_code, 200)

    def test_hybrid_search_endpoint(self):
        res = self.client.get("/api/knowledge/hybrid-search", params={"q": "protocol", "limit": 5})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("lab_results", body)
        self.assertIn("vault_results", body)

    def test_unified_search_endpoint(self):
        res = self.client.get("/api/search", params={"q": "lab coats", "mode": "hybrid", "limit": 5})
        self.assertEqual(res.status_code, 200)
        self.assertIn("lab_results", res.json())

    def test_page_domains_endpoint(self):
        res = self.client.get("/api/page-domains")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("domains", body)
        self.assertIn("sections", body)

    def test_documents_registry_endpoint(self):
        res = self.client.get("/api/documents/registry", params={"limit": 5})
        self.assertEqual(res.status_code, 200)

    def test_admin_ingestion_jobs_endpoint(self):
        res = self.client.get("/api/admin/ingestion-jobs")
        self.assertEqual(res.status_code, 200)

    def test_lab_sections_lists_processed_counts(self):
        res = self.client.get("/api/lab/sections")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body.get("processed_source"), "local_processed_json")
        wet = next((s for s in body.get("sections") or [] if s["section_id"] == "wet_lab_files"), None)
        self.assertIsNotNone(wet)
        if wet and wet.get("processed"):
            self.assertGreaterEqual(wet.get("extracted_document_count") or 0, 1)

    def test_lab_section_wet_lab_extracted_count(self):
        res = self.client.get("/api/lab/section/wet_lab_files")
        if res.status_code == 404:
            self.skipTest("wet_lab_files twin not on disk in this environment")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body.get("section_id"), "wet_lab_files")
        self.assertEqual(body.get("source"), "local_processed_json")
        extracted = (body.get("metrics") or {}).get("extracted_document_count")
        if extracted is None:
            extracted = (body.get("extraction") or {}).get("status_counts", {}).get("extracted")
        self.assertEqual(extracted, 461)
        self.assertGreaterEqual(body.get("document_index_count", 0), 400)
        preview = body.get("document_index_preview") or []
        self.assertGreater(len(preview), 0)
        self.assertTrue(any(".xlsx" in (d.get("path") or "") for d in preview))

    def test_lab_section_documents_pagination(self):
        res = self.client.get(
            "/api/lab/section/wet_lab_files/documents",
            params={"q": "Sectioning", "limit": 5},
        )
        if res.status_code == 404:
            self.skipTest("wet_lab_files twin not on disk")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertGreaterEqual(body.get("total", 0), 1)
        self.assertLessEqual(len(body.get("documents") or []), 5)


class TestVectorizationQueue(unittest.TestCase):
    def test_ome_tiff_not_eligible_for_vectorize(self):
        from scripts.build_raw_asset_inventory import vector_status

        self.assertEqual(vector_status(".tif", "image"), "metadata_summary_only")
        self.assertEqual(vector_status(".ome.tiff", "image"), "metadata_summary_only")
        self.assertEqual(vector_status(".pdf", "document"), "eligible_pending_review")


if __name__ == "__main__":
    unittest.main()
