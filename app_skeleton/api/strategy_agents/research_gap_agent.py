"""Knowledge gaps and underexplored research directions."""
from __future__ import annotations

from typing import Any

from app_skeleton.api.evidence_orchestrator import EvidencePackage, QueryUnderstanding
from app_skeleton.api.strategy_agents._base import agent_notes


class ResearchGapAgent:
    name = "research_gap"

    def analyze(
        self,
        package: EvidencePackage,
        *,
        understanding: QueryUnderstanding | None = None,
        question: str = "",
    ) -> dict[str, Any]:
        gaps: list[str] = []
        questions: list[str] = []

        if package.confidence in {"insufficient", "low"}:
            gaps.append("Indexed evidence is thin for a high-confidence strategic recommendation.")

        buckets = set(package.by_bucket.keys())
        if "research" not in buckets:
            gaps.append("External literature coverage is missing from retrieval.")
        if "lab" not in buckets and "file" not in buckets:
            gaps.append("Internal protocol/SOP evidence not retrieved.")
        if "project" not in buckets:
            gaps.append("Project digital twin context absent — link query to specific project codes.")

        for note in (package.validation_notes or [])[:4]:
            gaps.append(note)

        domains = understanding.domains if understanding else ()
        if "hgsc_immunology" in domains and "spatial_biology" not in domains:
            questions.append("How does spatial immune architecture differ across HGSC molecular subtypes?")
        if "spatial_biology" in domains:
            questions.append("Which spatial metrics best predict immunotherapy response in our cohorts?")
        if not questions:
            questions.append("What single experiment would most reduce uncertainty in the top hypothesis?")

        return {
            **agent_notes(package, self.name),
            "knowledge_gaps": gaps[:8],
            "research_questions": questions[:5],
        }
