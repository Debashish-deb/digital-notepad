"""Experiment suggestions, controls, feasibility."""
from __future__ import annotations

from typing import Any

from omeia.api.evidence_orchestrator import EvidencePackage, QueryUnderstanding


class ExperimentalDesignAgent:
    name = "experimental_design"

    def analyze(
        self,
        package: EvidencePackage,
        *,
        understanding: QueryUnderstanding | None = None,
        question: str = "",
    ) -> dict[str, Any]:
        domains = understanding.domains if understanding else ()
        experiments: list[str] = []
        controls: list[str] = ["Include biological replicates and batch-matched controls."]
        risks: list[str] = []
        feasibility = "medium"

        if "spatial_biology" in domains or "tcycif" in (question or "").lower():
            experiments.append("Pilot tCyCIF panel on n=8–12 slides spanning responder/non-responder strata.")
            controls.append("Matched H&E and autofluorescence controls per run.")
        if "hgsc_immunology" in domains:
            experiments.append("Multiplex IHC or spatial panel for TLS-associated markers (CD20, CD3, CXCL13).")
        if "clinical_translational" in domains:
            experiments.append("Retrospective chart review linking spatial metrics to treatment line and PFS.")
            risks.append("Clinical confounding if cohort heterogeneity is high.")

        if not experiments:
            experiments.append("Feasibility pilot (n=6–10) on highest-priority hypothesis from indexed evidence.")
        if package.confidence == "insufficient":
            feasibility = "low"
            risks.append("Insufficient indexed evidence — pilot may not justify full study launch.")
        elif package.confidence == "high":
            feasibility = "high"

        return {
            "agent": self.name,
            "experiments": experiments[:5],
            "controls": controls[:4],
            "risks": risks[:5],
            "feasibility": feasibility,
        }
