"""Tests for Supabase document sync (mocked DB; skip integration without hosted password)."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from app_skeleton.api import supabase_sync as ss


class TestTruncateAndEligibility(unittest.TestCase):
    def test_truncate_utf8_respects_multibyte(self) -> None:
        text = "ä" * 30_000
        out = ss.truncate_utf8(text, 100)
        self.assertLessEqual(len(out.encode("utf-8")), 104)

    def test_sanitize_metadata_truncates_preview(self) -> None:
        meta = {"text_preview": "x" * 100_000}
        out = ss.sanitize_metadata_json(meta, max_bytes=1000)
        self.assertLessEqual(len(out["text_preview"].encode("utf-8")), 1100)
        self.assertTrue(out.get("supabase_sync", {}).get("truncated"))

    def test_image_extension_excluded(self) -> None:
        row = {
            "extension": ".png",
            "asset_type": "image",
            "extraction_status": "metadata_only",
            "storage_provider": "local_database_mirror",
            "metadata_json": {},
        }
        self.assertFalse(ss.is_document_sync_eligible(row))

    def test_pdf_document_included(self) -> None:
        row = {
            "extension": ".pdf",
            "asset_type": "document",
            "extraction_status": "extracted",
            "storage_provider": "local_database_mirror",
            "metadata_json": {},
            "extracted_clean": "hello",
        }
        self.assertTrue(ss.is_document_sync_eligible(row))

    def test_supabase_storage_excluded(self) -> None:
        row = {
            "extension": ".pdf",
            "asset_type": "document",
            "extraction_status": "extracted",
            "storage_provider": "supabase_storage",
            "metadata_json": {},
        }
        self.assertFalse(ss.is_document_sync_eligible(row))


class TestSyncGuards(unittest.TestCase):
    def test_disabled_when_sync_not_enabled(self) -> None:
        with patch.dict(os.environ, {"SUPABASE_SYNC_ENABLED": "false"}, clear=False):
            result = ss.sync_documents_to_supabase()
        self.assertEqual(result["status"], "disabled")

    def test_needs_password_when_unset(self) -> None:
        env = {
            "SUPABASE_SYNC_ENABLED": "true",
            "SUPABASE_DB_PASSWORD": "",
            "POSTGRES_CONN": "postgresql://local/db",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch.object(ss, "supabase_hosted_password_set", return_value=False):
                result = ss.sync_documents_to_supabase()
        self.assertEqual(result["status"], "needs_user_decision")
        self.assertIn("SUPABASE_DB_PASSWORD", result["message"])

    @patch.object(ss, "write_sync_report")
    @patch.object(ss, "_fetch_local_candidates")
    @patch.object(ss, "hosted_postgres_conn")
    @patch.object(ss, "local_postgres_conn")
    @patch.object(ss, "supabase_hosted_password_set", return_value=True)
    @patch.object(ss, "supabase_sync_enabled", return_value=True)
    def test_dry_run_counts_candidates(
        self,
        _enabled: MagicMock,
        _pwd: MagicMock,
        local_conn: MagicMock,
        hosted_conn: MagicMock,
        fetch: MagicMock,
        _write: MagicMock,
    ) -> None:
        local_conn.return_value = "postgresql://local/db"
        hosted_conn.return_value = "postgresql://hosted/db"
        fetch.return_value = [{"asset_id": "a1"}, {"asset_id": "a2"}]
        with patch.object(ss, "_estimate_hosted_db_bytes", return_value=1000):
            result = ss.sync_documents_to_supabase(dry_run=True, limit=10)
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["would_sync"], 2)

    @patch.object(ss, "write_sync_report")
    @patch.object(ss, "_estimate_hosted_db_bytes", return_value=500_000_000)
    @patch.object(ss, "_fetch_local_candidates", return_value=[{"asset_id": "a1"}])
    @patch.object(ss, "hosted_postgres_conn", return_value="postgresql://hosted/db")
    @patch.object(ss, "local_postgres_conn", return_value="postgresql://local/db")
    @patch.object(ss, "supabase_hosted_password_set", return_value=True)
    @patch.object(ss, "supabase_sync_enabled", return_value=True)
    def test_skips_when_db_too_large(
        self,
        _enabled: MagicMock,
        _pwd: MagicMock,
        _local: MagicMock,
        _hosted: MagicMock,
        _fetch: MagicMock,
        _size: MagicMock,
        _write: MagicMock,
    ) -> None:
        result = ss.sync_documents_to_supabase()
        self.assertEqual(result["status"], "skipped_db_size")


@unittest.skipUnless(
    os.getenv("SUPABASE_DB_PASSWORD", "").strip() and os.getenv("SUPABASE_SYNC_INTEGRATION") == "1",
    "Set SUPABASE_DB_PASSWORD and SUPABASE_SYNC_INTEGRATION=1 for live hosted sync test",
)
class TestHostedIntegration(unittest.TestCase):
    def test_dry_run_against_hosted(self) -> None:
        result = ss.sync_documents_to_supabase(dry_run=True, limit=5)
        self.assertIn(result["status"], ("dry_run", "disabled", "needs_user_decision", "skipped_db_size"))
        self.assertIsInstance(result.get("document_rows_eligible"), int)


class TestKnowledgeFkSanitize(unittest.TestCase):
    def test_nulls_unknown_project_candidate_on_hosted(self) -> None:
        row = {
            "asset_id": "a1",
            "absolute_path": "/tmp/x.pdf",
            "logical_path": "projects/x.pdf",
            "filename": "x.pdf",
            "project_candidate_id": "missing-project",
            "ka_metadata_json": {},
        }
        payload = ss._knowledge_payload(row, max_bytes=1000, valid_project_ids={"known"})
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertIsNone(payload["project_candidate_id"])

    def test_keeps_valid_project_candidate(self) -> None:
        row = {
            "asset_id": "a2",
            "absolute_path": "/tmp/y.pdf",
            "logical_path": "projects/y.pdf",
            "filename": "y.pdf",
            "project_candidate_id": "known",
            "ka_metadata_json": {},
        }
        payload = ss._knowledge_payload(row, max_bytes=1000, valid_project_ids={"known"})
        self.assertEqual(payload["project_candidate_id"], "known")


class TestSyncReportIO(unittest.TestCase):
    def test_write_and_read_roundtrip(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sync_run_report.json"
            with patch.object(ss, "INGESTION_REPORTS_DIR", Path(td)):
                with patch.object(ss, "SYNC_REPORT_PATH", p):
                    ss.write_sync_report({"status": "ok", "document_rows_synced": 3})
                    loaded = ss.read_last_sync_report()
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded["status"], "ok")


if __name__ == "__main__":
    unittest.main()
