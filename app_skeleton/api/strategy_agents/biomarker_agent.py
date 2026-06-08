"""Biomarker evaluation and marker-panel reasoning."""
from __future__ import annotations

import re
from typing import Any

from app_skeleton.api.evidence_orchestrator import EvidencePackage
from app_skeleton.api.strategy_agents._base import INTERNAL_BUCKETS, filter_items, item_to_ref

BIOMARKER_RE = re.compile(
    r"\b(biomarker|marker|panel|cd\d+|pd-?l1|tim-?3|lag-?3|brca|tp53|mhc|hla|signature|prognostic|predictive)\b",
    re.I,
)


class BiomarkerAgent:
    name = "biomarker"

    def analyze(self, package: EvidencePackage, *, question: str = "") -> dict[str, Any]:
        items = filter_items(package, buckets=INTERNAL_BUCKETS | {"research"}, pattern=BIOMARKER_RE, limit=10)
        ranked = sorted(items, key=lambda i: i.score, reverse=True)
        refs = [item_to_ref(i) for i in ranked[:6]]

        suggestions: list[str] = []
        if len(ranked) >= 2:
            titles = ", ".join(i.title[:40] for i in ranked[:3])
            suggestions.append(f"Strongest indexed marker evidence: {titles}.")
            suggestions.append("Consider validating top markers in orthogonal assay (IHC + spatial).")
        elif ranked:
            suggestions.append("Single-source marker evidence — prioritize replication before portfolio decisions.")
        else:
            suggestions.append("No marker-specific evidence retrieved; review marker panel SOPs and cohort data.")

        combinations: list[str] = []
        genes = set()
        for item in ranked:
            for m in re.findall(r"\b(?:CD\d+|PD-?L1|TIM-?3|BRCA1?|TP53)\b", item.snippet, re.I):
                genes.add(m.upper())
        if len(genes) >= 2:
            combinations.append(f"Co-mentioned markers in evidence: {', '.join(sorted(genes)[:6])}.")

        return {
            "agent": self.name,
            "internal_refs": refs,
            "marker_suggestions": suggestions,
            "combinations": combinations,
            "evidence_strength": "high" if len(ranked) >= 4 else "medium" if ranked else "low",
        }
