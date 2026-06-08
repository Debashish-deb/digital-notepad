"""Computational workflows, datasets, and analysis plans."""
from __future__ import annotations

import re
from typing import Any

from omeia.api.evidence_orchestrator import EvidencePackage
from omeia.api.strategy_agents._base import EXTERNAL_BUCKETS, INTERNAL_BUCKETS, filter_items, item_to_ref

BIOINFO_RE = re.compile(
    r"\b(bioinformatics|rna-?seq|scrna|spatial transcriptomics|deconvolution|pipeline|"
    r"clustering|differential|gsea|pathway|dataset|gse\d+|tcga|ega|lumi|slurm|python|r\b)\b",
    re.I,
)


class BioinformaticsAgent:
    name = "bioinformatics"

    def analyze(self, package: EvidencePackage, *, question: str = "") -> dict[str, Any]:
        items = filter_items(package, buckets=INTERNAL_BUCKETS | EXTERNAL_BUCKETS, pattern=BIOINFO_RE, limit=10)
        refs = [item_to_ref(i) for i in items[:6]]

        workflows: list[str] = []
        if items:
            workflows.append("Prioritize reproducible pipelines documented in lab notebooks or analysis reports.")
            if any("lumi" in (i.snippet + i.title).lower() for i in items):
                workflows.append("LUMI/HPC workflows referenced — align compute plan with existing SLURM templates.")
            if any(re.search(r"gse\d+", i.snippet, re.I) for i in items):
                workflows.append("Public dataset accessions found — validate metadata and batch effects before integration.")
        else:
            workflows.append("No computational workflow evidence — document analysis plan in project twin.")

        validation: list[str] = [
            "Hold-out cohort or orthogonal assay validation for computational findings.",
            "Pre-register analysis parameters (clustering resolution, FDR thresholds).",
        ]

        return {
            "agent": self.name,
            "refs": refs,
            "workflows": workflows,
            "validation_analyses": validation,
        }
