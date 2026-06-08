"""Copilot API tests — in-process TestClient (no live server required)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from omeia.api.main import app
from tests.auth_fixtures import apply_auth_override, clear_auth_override


class TestCopilotPlatform(unittest.TestCase):
    def setUp(self) -> None:
        apply_auth_override("researcher")
        self.client = TestClient(app)

    def tearDown(self) -> None:
        clear_auth_override()

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("database_connected", data)

    @patch("omeia.api.routers.copilot.require_role")
    def test_ask_documentation_mode(self, _role_patch) -> None:
        response = self.client.post(
            "/ask",
            json={
                "question": "Install napari on macOS Apple Silicon.",
                "project_codes": ["SPACE", "EyeMT"],
                "mode": "documentation_only",
            },
        )
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertTrue(res.get("is_safe"))
        self.assertTrue(len(res.get("answer") or "") > 20)

    @patch("omeia.api.routers.copilot.require_role")
    def test_ask_search_only(self, _role_patch) -> None:
        response = self.client.post(
            "/ask",
            json={
                "question": "Ashlar stitching protocol",
                "project_codes": ["SPACE"],
                "mode": "search_only",
            },
        )
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertTrue(res.get("is_safe"))
        self.assertIsInstance(res.get("sources"), list)
        self.assertIn("intent", res)

    @patch("omeia.api.routers.copilot.require_role")
    def test_chat_ask_intent_parity(self, _role_patch) -> None:
        question = "What does Färkkilä Lab study?"
        chat_r = self.client.post(
            "/api/chat",
            json={"message": question, "project_codes": ["SPACE"], "stream": False},
        )
        ask_r = self.client.post(
            "/ask",
            json={"question": question, "project_codes": ["SPACE"], "mode": "documentation_only"},
        )
        self.assertEqual(chat_r.status_code, 200)
        self.assertEqual(ask_r.status_code, 200)
        chat_j = chat_r.json()
        ask_j = ask_r.json()
        self.assertEqual(chat_j.get("intent"), ask_j.get("intent"))
        self.assertEqual(chat_j.get("use_rag"), ask_j.get("use_rag"))

    @patch("omeia.api.routers.copilot.require_role")
    def test_install_recipes(self, _role_patch) -> None:
        response = self.client.post(
            "/install_guide",
            json={"tool_name": "napari", "os_platform": "linux"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("mamba", data["script"].lower())

    @patch("omeia.api.routers.copilot.require_role")
    def test_lumi_script_builder(self, _role_patch) -> None:
        response = self.client.post(
            "/lumi_job",
            json={
                "job_name": "test_job",
                "project_account": "project_462001415",
                "use_gpu": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("#SBATCH --job-name=test_job", data["script"])

    @patch("omeia.api.routers.copilot.require_role")
    def test_log_parser(self, _role_patch) -> None:
        response = self.client.post(
            "/parse_log",
            json={"log_text": "Slurm task terminated: Out of memory (exit code 137)"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["cause"])

    @patch("omeia.api.routers.copilot.require_role")
    def test_environment_checkers(self, _role_patch) -> None:
        response = self.client.post(
            "/run_checker",
            json={"checker_name": "python_env"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("stdout", data)


if __name__ == "__main__":
    unittest.main()
