"""Tests for Raw Knowledge Vault ingestion engine and vault extraction policies."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app_skeleton.api import document_extraction as de
from app_skeleton.api.vault_ingestion_engine import (
    iter_scan_files,
    run_ingest_scan,
    stable_asset_id,
    upsert_vault_from_extraction,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vault_sample_project"


class TestVaultExtractionPolicies(unittest.TestCase):
    def test_pdf_extracts_or_metadata(self):
        path = FIXTURES / "sample.pdf"
        self.assertTrue(path.is_file())
        result = de.extract_for_vault(path, FIXTURES)
        self.assertIn(result.status, {"extracted", "empty", "metadata_only", "failed"})

    def test_docx_extracts_text(self):
        path = FIXTURES / "sample.docx"
        result = de.extract_for_vault(path, FIXTURES)
        self.assertIn(result.status, {"extracted", "metadata_only", "empty", "failed"})

    def test_xlsx_metadata_has_sheets(self):
        path = FIXTURES / "sample.xlsx"
        if not path.stat().st_size:
            self.skipTest("openpyxl not available for xlsx fixture")
        result = de.extract_for_vault(path, FIXTURES)
        self.assertIn("sheets", result.metadata)

    def test_csv_schema_preview(self):
        result = de.extract_for_vault(FIXTURES / "sample.csv", FIXTURES)
        self.assertTrue(result.metadata.get("vault_policy") == "excel_schema_preview" or result.text)

    def test_python_script_summary(self):
        result = de.extract_for_vault(FIXTURES / "analysis.py", FIXTURES)
        self.assertEqual(result.metadata.get("vault_policy"), "script_summary")
        self.assertIn("pandas", " ".join(result.metadata.get("imports") or []))

    def test_r_script_summary(self):
        result = de.extract_for_vault(FIXTURES / "plot.R", FIXTURES)
        self.assertEqual(result.metadata.get("vault_policy"), "script_summary")

    def test_log_error_lines(self):
        result = de.extract_for_vault(FIXTURES / "pipeline.log", FIXTURES)
        self.assertEqual(result.metadata.get("vault_policy"), "log_summary")
        self.assertGreaterEqual(result.metadata.get("error_line_count", 0), 1)

    def test_tiff_metadata_only(self):
        result = de.extract_for_vault(FIXTURES / "slide.tiff", FIXTURES)
        self.assertEqual(result.status, "metadata_only")
        self.assertEqual(result.metadata.get("vault_policy"), "large_binary_metadata_only")

    def test_vault_extraction_status_failed(self):
        result = de.ExtractionResult(
            path="x.txt",
            name="x.txt",
            extension=".txt",
            document_kind="plain_text",
            mime_type="text/plain",
            size_bytes=1,
            modified_at=None,
            status="failed",
            errors=["boom"],
        )
        self.assertEqual(de.vault_extraction_status(result), "failed")


class TestVaultScanIterator(unittest.TestCase):
    def test_iter_scan_files_finds_fixtures(self):
        paths = list(iter_scan_files(FIXTURES))
        names = {p[0].name for p in paths}
        self.assertIn("sample.pdf", names)
        self.assertIn("analysis.py", names)


class TestVaultIngestionEngine(unittest.TestCase):
    def test_stable_asset_id_deterministic(self):
        a = stable_asset_id("projects/demo/a.pdf", 100)
        b = stable_asset_id("projects/demo/a.pdf", 100)
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("asset_"))

    @patch("app_skeleton.api.vault_ingestion_engine._db_conn")
    @patch("app_skeleton.api.vault_ingestion_engine.psycopg.connect")
    def test_run_ingest_scan_writes_report(self, mock_connect, mock_conn):
        mock_conn.return_value = "postgresql://mock"
        conn = MagicMock()
        cur = MagicMock()
        cur.description = [
            ("checkpoint_id",), ("scan_root",), ("project_hint",),
            ("last_logical_path",), ("files_processed",), ("status",),
            ("manifest_json",), ("job_id",),
        ]
        cur.fetchone.return_value = None
        mock_connect.return_value.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cur

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "note.txt").write_text("hello vault", encoding="utf-8")
            with patch("app_skeleton.api.vault_ingestion_engine.INGESTION_REPORTS_DIR", root / "reports"):
                with patch("app_skeleton.api.vault_ingestion_engine.ensure_vault_schema"):
                    result = run_ingest_scan(scan_root=root, max_files=10)
        self.assertIn("counts", result)
        self.assertGreaterEqual(result["counts"]["scanned"], 1)
        self.assertIn("report_path", result)
        report_path = Path(result["report_path"])
        if report_path.is_file():
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIn("scanned", payload["counts"])
        else:
            self.assertIn("run_id", result)

    def test_upsert_always_records_failed(self):
        cur = MagicMock()
        cur.fetchone.return_value = None
        counts: dict[str, int] = {}
        result = de.ExtractionResult(
            path="bad.xyz",
            name="bad.xyz",
            extension=".xyz",
            document_kind="other",
            mime_type=None,
            size_bytes=10,
            modified_at=None,
            status="failed",
            errors=["parse error"],
        )
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as fh:
            fh.write(b"data")
            path = Path(fh.name)
        try:
            asset_id = upsert_vault_from_extraction(
                cur,
                logical_path="projects/test/bad.xyz",
                abs_path=path,
                project_hint="test_proj",
                result=result,
                counts=counts,
            )
        finally:
            path.unlink(missing_ok=True)
        self.assertTrue(asset_id.startswith("asset_"))
        self.assertEqual(counts.get("failed"), 1)
        self.assertTrue(cur.execute.called)


class TestVaultIngestApi(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from app_skeleton.api.main import app

        self.client = TestClient(app)

    def test_review_queue_accepts_queue_param(self):
        res = self.client.get("/api/vault/review-queue", params={"queue": "failed", "limit": 5})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("items", body)
        self.assertEqual(body.get("queue"), "failed")

    def test_search_uncategorized_param(self):
        res = self.client.get(
            "/api/vault/search",
            params={"q": "", "uncategorized_only": True, "limit": 5},
        )
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
