"""Data Pad service — path safety, backups, proofread structure."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omeia.api import datapad_service as dp


class TestDatapadPathSafety(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.project = "TestProj"
        proj_dir = self.root / "1_TestProj"
        proj_dir.mkdir()
        (proj_dir / "01_Management").mkdir()
        self.doc = proj_dir / "01_Management" / "notes.md"
        self.doc.write_text("# Hello\n\nBody text.", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @patch("omeia.api.datapad_service.get_content_root")
    @patch("omeia.api.datapad_service.find_project_folder")
    @patch("omeia.api.datapad_service.projects_roots_for_scan")
    def test_read_and_save_with_backup(self, mock_scan, mock_find, mock_content) -> None:
        proj = self.root / "1_TestProj"
        mock_find.return_value = proj
        mock_content.return_value = proj
        mock_scan.return_value = [proj]

        with patch.object(dp, "DATAPAD_EDIT_ENABLED", True):
            doc = dp.read_section_document(self.project, "01_Management/notes.md")
            self.assertIn("Hello", doc["content"])
            self.assertTrue(doc["etag"])

            saved = dp.save_section_document(
                self.project,
                "01_Management/notes.md",
                "# Hello\n\nUpdated body.",
                actor="test@helsinki.fi",
                create_backup=True,
            )
            self.assertEqual(saved["status"], "saved")
            self.assertTrue(saved.get("backup_path"))

            on_disk = self.doc.read_text(encoding="utf-8")
            self.assertIn("Updated body", on_disk)

    @patch("omeia.api.datapad_service.get_content_root")
    @patch("omeia.api.datapad_service.find_project_folder")
    @patch("omeia.api.datapad_service.projects_roots_for_scan")
    def test_path_traversal_blocked(self, mock_scan, mock_find, mock_content) -> None:
        proj = self.root / "1_TestProj"
        mock_find.return_value = proj
        mock_content.return_value = proj
        mock_scan.return_value = [proj]

        with self.assertRaises((FileNotFoundError, ValueError)):
            dp.read_section_document(self.project, "../../etc/passwd")

    @patch("omeia.api.datapad_service.get_content_root")
    @patch("omeia.api.datapad_service.find_project_folder")
    @patch("omeia.api.datapad_service.projects_roots_for_scan")
    def test_conflict_on_stale_etag(self, mock_scan, mock_find, mock_content) -> None:
        proj = self.root / "1_TestProj"
        mock_find.return_value = proj
        mock_content.return_value = proj
        mock_scan.return_value = [proj]

        with patch.object(dp, "DATAPAD_EDIT_ENABLED", True):
            doc = dp.read_section_document(self.project, "01_Management/notes.md")
            with self.assertRaises(dp.ConflictError):
                dp.save_section_document(
                    self.project,
                    "01_Management/notes.md",
                    "changed",
                    expected_etag='"stale-etag"',
                )
            del doc


class TestDatapadProofread(unittest.TestCase):
    def test_proofread_returns_structure(self) -> None:
        with patch.object(dp, "datapad_ai_available", return_value=False):
            result = dp.proofread_content("teh quick brown  recieve")
            self.assertIn("fixes", result)
            self.assertIn("corrected_text", result)
            self.assertIn("mode", result)
            self.assertIn("the", result["corrected_text"].lower())
            self.assertTrue(isinstance(result["fixes"], list))

    def test_suggest_headings_rules(self) -> None:
        with patch.object(dp, "datapad_ai_available", return_value=False):
            result = dp.suggest_headings("Plain paragraph without headings.\n\nMore text.")
            self.assertIn("suggestions", result)
            self.assertIn("headings", result)
            self.assertEqual(result["mode"], "rules")


class TestDatapadEditGate(unittest.TestCase):
    def test_save_disabled_when_flag_off(self) -> None:
        with patch.object(dp, "DATAPAD_EDIT_ENABLED", False):
            with self.assertRaises(PermissionError):
                dp.save_section_document("X", "a.md", "x")


if __name__ == "__main__":
    unittest.main()
