"""Smoke tests for /api/chat status and guardrails (no live Gemini required)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app_skeleton.api.llm_client import LLMClient
from app_skeleton.api.main import app
from app_skeleton.api.privacy_guardrails import audit_message, guard_for_llm
from tests.auth_fixtures import apply_auth_override, clear_auth_override


class TestPrivacyGuardrails(unittest.TestCase):
    def test_audit_redacts_email(self) -> None:
        audit = audit_message("Contact patient at john.doe@example.com about sample S12345")
        self.assertGreater(audit.get("redaction_count", 0), 0)
        self.assertIn("[REDACTED_", audit.get("redacted_text", ""))

    def test_external_llm_blocked_for_pii(self) -> None:
        _, audit, limitations = guard_for_llm("Patient #ABC123 needs review", "gemini")
        self.assertTrue(any("blocked" in note.lower() for note in limitations))


class TestChatApi(unittest.TestCase):
    def setUp(self) -> None:
        apply_auth_override("researcher")
        self.client = TestClient(app)

    def tearDown(self) -> None:
        clear_auth_override()

    def test_chat_status_returns_provider_info(self) -> None:
        response = self.client.get("/api/chat/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("chat_provider", data)
        self.assertIn("llm", data)
        self.assertIn("provider", data["llm"])

    @patch("app_skeleton.api.routers.chat.require_role")
    def test_chat_message_mock_mode(self, _role_patch) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "How do I install napari on macOS?",
                "project_codes": ["SPACE"],
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("answer"))
        self.assertIn("provider", data)
        self.assertTrue(data.get("is_safe"))

    @patch("app_skeleton.api.routers.chat.require_role")
    def test_chat_greeting_skips_rag_and_sources(self, _role_patch) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "hi",
                "project_codes": ["SPACE"],
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("answer"))
        self.assertEqual(data.get("intent"), "smalltalk")
        self.assertFalse(data.get("use_rag"))
        self.assertFalse(data.get("show_sources"))
        self.assertEqual(data.get("sources"), [])
        self.assertEqual(data.get("search_hits"), [])
        self.assertEqual(data.get("limitations"), [])

    @patch("app_skeleton.api.routers.chat.require_role")
    @patch("app_skeleton.api.routers.chat._chat_llm")
    def test_mock_fallback_reports_honest_provenance(self, chat_llm_patch, _role_patch) -> None:
        forced = LLMClient()
        forced.provider = "gemini"
        forced.model = "gemini-3.5-flash"
        forced.api_key = ""
        forced._init_client()

        def _fail_generate(prompt: str, system_prompt: str = "") -> str:
            forced._record_synthesis(
                configured_primary="gemini",
                effective_provider="mock",
                model="mock-model",
                fallback_used=True,
            )
            return forced._mock_generate(prompt, system_prompt)

        forced.generate = _fail_generate  # type: ignore[method-assign]
        chat_llm_patch.return_value = forced

        response = self.client.post(
            "/api/chat",
            json={"message": "What is BaSiC illumination correction?", "project_codes": ["SPACE"]},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("synthesis_mode"), "mock")
        self.assertTrue(data.get("fallback_used"))
        self.assertEqual(data.get("effective_provider"), "mock")
        self.assertNotEqual(data.get("provider"), "gemini")


class TestAuthFixtures(unittest.TestCase):
    def test_roles_override_without_401(self) -> None:
        for role in ("researcher", "viewer", "editor", "admin"):
            with self.subTest(role=role):
                apply_auth_override(role)
                client = TestClient(app)
                response = client.get("/api/chat/status")
                self.assertEqual(response.status_code, 200, msg=f"role={role}")
                clear_auth_override()


if __name__ == "__main__":
    unittest.main()
