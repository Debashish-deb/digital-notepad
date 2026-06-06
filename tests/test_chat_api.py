"""Smoke tests for /api/chat status and guardrails (no live Gemini required)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app_skeleton.api.main import app
from app_skeleton.api.privacy_guardrails import audit_message, guard_for_llm


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
        self.client = TestClient(app)

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


if __name__ == "__main__":
    unittest.main()
