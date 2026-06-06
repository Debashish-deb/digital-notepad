"""Unit tests for chat intent classification."""
from __future__ import annotations

import unittest

from app_skeleton.api.chat_intent import classify_chat_intent


class TestChatIntent(unittest.TestCase):
    def test_hi_is_smalltalk_without_rag(self) -> None:
        decision = classify_chat_intent("hi")
        self.assertEqual(decision.intent, "smalltalk")
        self.assertFalse(decision.use_rag)
        self.assertFalse(decision.show_sources)
        self.assertFalse(decision.require_citations)

    def test_mhc_research_question_uses_rag(self) -> None:
        decision = classify_chat_intent("What is MHC class II in HGSC?")
        self.assertEqual(decision.intent, "research_question")
        self.assertTrue(decision.use_rag)
        self.assertTrue(decision.show_sources)
        self.assertTrue(decision.require_citations)

    def test_ashlar_protocol_question_uses_rag(self) -> None:
        decision = classify_chat_intent("How do I run Ashlar stitching?")
        self.assertEqual(decision.intent, "protocol_question")
        self.assertTrue(decision.use_rag)
        self.assertTrue(decision.show_sources)
        self.assertTrue(decision.require_citations)

    def test_gemini_setup_is_app_help_without_rag(self) -> None:
        decision = classify_chat_intent("How do I set up Gemini?")
        self.assertEqual(decision.intent, "app_help")
        self.assertFalse(decision.use_rag)
        self.assertFalse(decision.show_sources)
        self.assertFalse(decision.require_citations)

    def test_ingest_help_without_rag(self) -> None:
        decision = classify_chat_intent("How do I ingest a document into Qdrant for RAG?")
        self.assertEqual(decision.intent, "document_ingestion_help")
        self.assertFalse(decision.use_rag)
        self.assertFalse(decision.show_sources)

    def test_find_gse_uses_rag(self) -> None:
        decision = classify_chat_intent("Find GSE211956")
        self.assertEqual(decision.intent, "search_request")
        self.assertTrue(decision.use_rag)

    def test_bare_gse_accession_uses_rag(self) -> None:
        decision = classify_chat_intent("GSE211956")
        self.assertEqual(decision.intent, "search_request")
        self.assertTrue(decision.use_rag)


if __name__ == "__main__":
    unittest.main()
