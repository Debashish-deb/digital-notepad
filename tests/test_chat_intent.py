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

    def test_ingest_rag_phrase_not_protocol(self) -> None:
        decision = classify_chat_intent("How do I ingest documents into RAG?")
        self.assertEqual(decision.intent, "document_ingestion_help")
        self.assertNotEqual(decision.intent, "protocol_question")

    def test_find_gse_uses_rag(self) -> None:
        decision = classify_chat_intent("Find GSE211956")
        self.assertEqual(decision.intent, "search_request")
        self.assertTrue(decision.use_rag)

    def test_bare_gse_accession_uses_rag(self) -> None:
        decision = classify_chat_intent("GSE211956")
        self.assertEqual(decision.intent, "search_request")
        self.assertTrue(decision.use_rag)

    def test_farkkila_lab_overview_is_research(self) -> None:
        decision = classify_chat_intent("What does Färkkilä Lab study?")
        self.assertEqual(decision.intent, "research_question")
        self.assertTrue(decision.use_rag)
        self.assertTrue(decision.require_citations)

    def test_spatial_transcriptomics_research(self) -> None:
        decision = classify_chat_intent("What datasets exist for spatial transcriptomics?")
        self.assertEqual(decision.intent, "research_question")
        self.assertTrue(decision.use_rag)

    def test_explicit_search_request(self) -> None:
        decision = classify_chat_intent("Where is the GeoMx DSP manual?")
        self.assertEqual(decision.intent, "search_request")
        self.assertTrue(decision.use_rag)

    def test_tls_research_not_protocol(self) -> None:
        decision = classify_chat_intent("Explain tertiary lymphoid structures in ovarian cancer")
        self.assertEqual(decision.intent, "research_question")
        self.assertNotEqual(decision.intent, "protocol_question")

    def test_visium_research(self) -> None:
        decision = classify_chat_intent("How is Visium used in HGSC studies?")
        self.assertEqual(decision.intent, "research_question")

    def test_short_generic_skips_rag(self) -> None:
        decision = classify_chat_intent("thanks")
        self.assertEqual(decision.intent, "smalltalk")
        self.assertFalse(decision.use_rag)

    def test_patient_id_sensitive(self) -> None:
        decision = classify_chat_intent("Patient #ABC123 needs review")
        self.assertEqual(decision.intent, "sensitive_private")
        self.assertFalse(decision.use_rag)


if __name__ == "__main__":
    unittest.main()
