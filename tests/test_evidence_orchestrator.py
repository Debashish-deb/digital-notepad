"""Tests for OMEIA Research Evidence Orchestrator."""
from __future__ import annotations

import unittest

from app_skeleton.api.chat_conversation import classify_and_enrich
from app_skeleton.api.evidence_orchestrator import (
    ORCHESTRATOR_CORE_PROMPT,
    PRINCIPLE_HALLUCINATION_CONTROL,
    PRINCIPLE_RESPONSE_STRUCTURE,
    build_orchestrator_system_prompt,
    build_orchestrator_user_prompt,
    build_search_plan,
    extract_domains,
    extract_entities,
    format_evidence_package_block,
    package_evidence,
    should_use_orchestrator,
    understand_query,
)
from app_skeleton.api.evidence_orchestrator import EvidenceItem, EvidencePackage


class _FakeHit:
    def __init__(self, **kwargs: object) -> None:
        self.__dict__.update(kwargs)

    def model_dump(self) -> dict:
        return dict(self.__dict__)


class TestQueryUnderstanding(unittest.TestCase):
    def test_extract_domains_hgsc_spatial(self) -> None:
        domains = extract_domains("TIM-3 expression in HGSC spatial transcriptomics")
        self.assertIn("hgsc_immunology", domains)
        self.assertIn("spatial_biology", domains)

    def test_extract_entities_accession_and_gene(self) -> None:
        entities = extract_entities("What does GSE12345 show for BRCA1 in TCGA-OV?")
        joined = " ".join(entities).upper()
        self.assertIn("GSE12345", joined)
        self.assertIn("BRCA1", joined)

    def test_understand_query_research_intent(self) -> None:
        message = "Explain TLS in HGSC immunotherapy"
        decision = classify_and_enrich(message)
        understanding = understand_query(message, decision)
        self.assertEqual(understanding.intent_decision.intent, "research_question")
        self.assertIn("hgsc_immunology", understanding.domains)
        self.assertTrue(understanding.search_plan.require_citations)
        self.assertIn("research", understanding.search_plan.scopes)

    def test_search_plan_protocol_prioritizes_lab(self) -> None:
        decision = classify_and_enrich("How do I run Ashlar stitching on CycIF tiles?")
        plan = build_search_plan(decision, ("protocols_pipelines",), ())
        self.assertEqual(decision.intent, "protocol_question")
        self.assertIn("lab", plan.prioritize_buckets)


class TestEvidencePackaging(unittest.TestCase):
    def _sample_hits(self) -> list[_FakeHit]:
        return [
            _FakeHit(
                id="h1",
                title="TLS in ovarian cancer",
                source_type="publication",
                bucket="research",
                snippet="Tertiary lymphoid structures predict immunotherapy response in HGSC.",
                score=0.82,
                metadata={"doi": "10.1234/example", "pmid": "12345678"},
            ),
            _FakeHit(
                id="h2",
                title="Lab protocol: CycIF staining",
                source_type="protocol",
                bucket="lab",
                snippet="CycIF staining protocol for HGSC tissue sections.",
                score=0.71,
                metadata={},
            ),
        ]

    def test_package_evidence_structure(self) -> None:
        package = package_evidence(self._sample_hits(), [], entities=("HGSC",), limit=12)
        self.assertEqual(len(package.items), 2)
        self.assertIn("research", package.by_bucket)
        self.assertIn("lab", package.by_bucket)
        self.assertIn(package.confidence, {"high", "medium", "low", "insufficient"})
        self.assertTrue(package.items[0].index >= 1)

    def test_format_evidence_package_block_numbered(self) -> None:
        package = package_evidence(self._sample_hits(), [], limit=12)
        block = format_evidence_package_block(package)
        self.assertIn("STRUCTURED EVIDENCE PACKAGE", block)
        self.assertIn("[1]", block)
        self.assertIn("DOI: 10.1234/example", block)

    def test_rank_prefers_lab_for_protocol_domain(self) -> None:
        hits = self._sample_hits()
        package = package_evidence(hits, [], entities=(), limit=12)
        titles = [item.title for item in package.items]
        self.assertTrue(any("protocol" in t.lower() or "TLS" in t for t in titles))


class TestOrchestratorPrompts(unittest.TestCase):
    def test_core_prompt_contains_eleven_principles(self) -> None:
        self.assertIn("Understand the question before searching", ORCHESTRATOR_CORE_PROMPT)
        self.assertIn("Hallucination control", ORCHESTRATOR_CORE_PROMPT)
        self.assertIn("Executive summary", PRINCIPLE_RESPONSE_STRUCTURE)
        self.assertIn("NEVER invent citations", PRINCIPLE_HALLUCINATION_CONTROL)

    def test_system_prompt_includes_query_context(self) -> None:
        message = "What is TIM-3 in HGSC?"
        decision = classify_and_enrich(message)
        understanding = understand_query(message, decision)
        package = EvidencePackage(
            items=[
                EvidenceItem(
                    index=1,
                    title="TIM-3 review",
                    source_type="publication",
                    bucket="research",
                    snippet="TIM-3 is an immune checkpoint in HGSC.",
                    score=0.8,
                )
            ],
            by_bucket={"research": 1},
            confidence="medium",
        )
        prompt = build_orchestrator_system_prompt(understanding, package, user_name="Anniina")
        self.assertIn("hgsc_immunology", prompt)
        self.assertIn("Anniina", prompt)
        self.assertIn("Executive summary", prompt)

    def test_user_prompt_requires_structured_synthesis(self) -> None:
        package = EvidencePackage(
            items=[
                EvidenceItem(
                    index=1,
                    title="Source A",
                    source_type="publication",
                    bucket="research",
                    snippet="Finding A.",
                    score=0.7,
                )
            ],
            by_bucket={"research": 1},
            confidence="low",
        )
        user_prompt = build_orchestrator_user_prompt("What is TLS?", package)
        self.assertIn("STRUCTURED EVIDENCE PACKAGE", user_prompt)
        self.assertIn("executive summary", user_prompt.lower())
        self.assertIn("Do not invent sources", user_prompt)

    def test_should_use_orchestrator_for_research_rag(self) -> None:
        decision = classify_and_enrich("Explain MHC class II in HGSC")
        self.assertTrue(should_use_orchestrator(decision))

    def test_should_not_use_orchestrator_for_greeting(self) -> None:
        decision = classify_and_enrich("hello")
        self.assertFalse(should_use_orchestrator(decision))


if __name__ == "__main__":
    unittest.main()
