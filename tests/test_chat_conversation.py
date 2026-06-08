"""Tests for natural conversational greeting + intent enrichment."""
from __future__ import annotations

import unittest

from omeia.api.chat_conversation import (
    INTENT_GREETING,
    INTENT_QUESTION,
    classify_and_enrich,
    instant_greeting_response,
    is_pure_greeting,
    should_use_instant_greeting,
    UserChatContext,
)
from omeia.api.chat_service import answer_chat


class TestChatConversation(unittest.TestCase):
    def test_pure_greeting_detection(self) -> None:
        self.assertTrue(is_pure_greeting("hello"))
        self.assertTrue(is_pure_greeting("Good morning!"))
        self.assertTrue(is_pure_greeting("thanks"))
        self.assertFalse(is_pure_greeting("Can you explain TIM-3 in HGSC?"))

    def test_greeting_enriched_category(self) -> None:
        decision = classify_and_enrich("hi")
        self.assertEqual(decision.intent, "smalltalk")
        self.assertEqual(decision.intent_category, INTENT_GREETING)
        self.assertGreaterEqual(decision.confidence, 0.9)

    def test_research_question_not_greeting(self) -> None:
        decision = classify_and_enrich("Can you explain TIM-3 expression in HGSC?")
        self.assertEqual(decision.intent, "research_question")
        self.assertEqual(decision.intent_category, INTENT_QUESTION)
        self.assertTrue(decision.use_rag)

    def test_eyemt_project_maps_to_project_category(self) -> None:
        from omeia.api.chat_conversation import INTENT_PROJECT

        decision = classify_and_enrich("tell more about EYEMT project")
        self.assertEqual(decision.intent, "project_question")
        self.assertEqual(decision.intent_category, INTENT_PROJECT)
        self.assertTrue(decision.use_rag)

    def test_instant_greeting_no_capability_brochure(self) -> None:
        reply = instant_greeting_response("hello", UserChatContext())
        self.assertNotIn("OMEIA Research Copilot", reply)
        self.assertNotIn("I can help with", reply)
        self.assertNotIn("capabilities", reply.lower())
        self.assertTrue(any(word in reply.lower() for word in ("what", "working", "help", "explore", "looking", "project")))

    def test_instant_greeting_with_projects(self) -> None:
        ctx = UserChatContext(project_codes=("SPACE", "EyeMT"), project_labels=("SPACE", "EyeMT"))
        reply = instant_greeting_response("hi", ctx)
        self.assertIn("SPACE", reply)
        self.assertNotIn("literature and evidence synthesis", reply.lower())

    def test_should_use_instant_for_hi(self) -> None:
        decision = classify_and_enrich("hi")
        self.assertTrue(should_use_instant_greeting(decision, "hi"))

    def test_should_use_instant_for_how_are_doing_today(self) -> None:
        decision = classify_and_enrich("how are doing today?")
        self.assertEqual(decision.intent, "smalltalk")
        self.assertTrue(should_use_instant_greeting(decision, "how are doing today?"))

    def test_instant_greeting_how_are_doing(self) -> None:
        reply = instant_greeting_response("how are doing today?", UserChatContext())
        self.assertIn("Doing well", reply)
        self.assertNotIn("mock synthesis", reply.lower())

    def test_answer_chat_greeting_uses_template(self) -> None:
        from unittest.mock import MagicMock

        llm = MagicMock()
        llm.provider = "gemini"
        llm.model = "gemini-3.5-flash"
        llm.generate.side_effect = AssertionError("LLM should not run for pure greetings")

        result = answer_chat(
            "hello",
            project_codes=["SPACE"],
            user={"display_name": "Anniina"},
            llm=llm,
            search_svc=MagicMock(),
            rag_agent=MagicMock(),
        )
        self.assertEqual(result.get("synthesis_mode"), "template")
        self.assertEqual(result.get("intent"), "smalltalk")
        self.assertFalse(result.get("use_rag"))
        self.assertNotIn("OMEIA Research Copilot", result.get("answer", ""))
        llm.generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
