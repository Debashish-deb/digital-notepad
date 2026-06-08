"""Smoke tests for /api/chat status and guardrails (no live Gemini required)."""
from __future__ import annotations

import re
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from omeia.api.answer_grounding_service import enforce_citations, validate_answer_sources
from omeia.api.llm_client import LLMClient
from omeia.api.main import app
from omeia.api.privacy_guardrails import audit_message, guard_for_llm
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

    @patch("omeia.api.routers.chat.require_role")
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

    @patch("omeia.api.routers.chat.require_role")
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

    @patch("omeia.api.routers.chat.require_role")
    @patch("omeia.api.routers.chat._chat_llm")
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

    @patch("omeia.api.routers.chat.require_role")
    def test_off_topic_returns_labeled_refusal(self, _role_patch) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "What is the quantum chromodynamics of quark-gluon plasma in 12 dimensions?",
                "project_codes": ["SPACE"],
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        answer = (data.get("answer") or "").lower()
        self.assertTrue(
            "lab" in answer or "copilot" in answer or "general knowledge" in answer,
            msg=data.get("answer"),
        )
        self.assertTrue(any("off-topic" in (n or "").lower() for n in data.get("limitations") or []))

    @patch("omeia.api.routers.chat.require_role")
    @patch("omeia.api.routers.chat.rag_agent")
    @patch("omeia.api.routers.chat._chat_llm")
    def test_empty_corpus_honest_answer(self, chat_llm_patch, rag_patch, _role_patch) -> None:
        mock_llm = LLMClient()
        mock_llm.provider = "mock"
        chat_llm_patch.return_value = mock_llm
        rag_patch.retrieve.return_value = []

        with patch("omeia.api.routers.chat.SearchService") as search_cls:
            search_instance = MagicMock()
            search_instance.hits_for_copilot.return_value = []
            search_cls.return_value = search_instance

            response = self.client.post(
                "/api/chat",
                json={"message": "What is MHC class II in HGSC?", "project_codes": ["SPACE"]},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("indexed evidence", (data.get("answer") or "").lower())
        self.assertEqual(data.get("sources"), [])


class TestCitationEnforcement(unittest.TestCase):
    def test_enforce_citations_reprompts_then_appends(self) -> None:
        hits = [{"title": "Paper A", "snippet": "MHC class II"}]
        calls: list[str] = []

        def fake_gen(prompt: str, _system: str) -> str:
            calls.append(prompt)
            if len(calls) == 1:
                return "MHC class II is important in HGSC."
            if "IMPORTANT" in prompt:
                return "MHC class II is important in HGSC [1]."
            return "fallback"

        answer, notes = enforce_citations(
            "MHC class II is important in HGSC.",
            hits,
            generate_fn=fake_gen,
            user_content="question",
            system_prompt="sys",
        )
        self.assertTrue(re.search(r"\[1\]", answer))
        self.assertLessEqual(len(calls), 2)

    def test_validate_detects_missing_citations(self) -> None:
        result = validate_answer_sources("No markers here.", [{"title": "A"}])
        self.assertFalse(result["has_citations"])
        self.assertIsNotNone(result["warning"])


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
