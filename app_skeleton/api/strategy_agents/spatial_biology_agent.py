"""Tumor microenvironment and spatial/multiplex imaging reasoning."""
from __future__ import annotations

import re
from typing import Any

from app_skeleton.api.evidence_orchestrator import EvidencePackage
from app_skeleton.api.strategy_agents._base import INTERNAL_BUCKETS, filter_items, item_to_ref

SPATIAL_RE = re.compile(
    r"\b(spatial|tme|microenvironment|tls|stromal|immune niche|cycif|tcycif|imc|multiplex|"
    r"cell-?cell|neighborhood|deconvolution|visium|geomx)\b",
    re.I,
)


class SpatialBiologyAgent:
    name = "spatial_biology"

    def analyze(self, package: EvidencePackage, *, question: str = "") -> dict[str, Any]:
        items = filter_items(package, buckets=INTERNAL_BUCKETS | {"research"}, pattern=SPATIAL_RE, limit=10)
        refs = [item_to_ref(i) for i in items[:6]]

        patterns: list[str] = []
        if any("tcycif" in (i.snippet + i.title).lower() for i in items):
            patterns.append("tCyCIF / multiplex imaging workflows appear in indexed lab materials.")
        if any("tls" in (i.snippet + i.title).lower() for i in items):
            patterns.append("Tertiary lymphoid structure (TLS) context present in retrieved evidence.")
        if any("spatial" in (i.snippet + i.title).lower() for i in items):
            patterns.append("Spatial assay or analysis context supports TME-focused directions.")

        if not patterns:
            patterns.append("Limited spatial biology evidence — ingest spatial analysis reports or tCyCIF SOPs.")

        interactions: list[str] = []
        if len(items) >= 2:
            interactions.append("Cross-compare immune-stromal spatial patterns across cohort slides.")
            interactions.append("Map cell-cell interaction metrics to clinical endpoints where available.")

        return {
            "agent": self.name,
            "internal_refs": refs,
            "spatial_patterns": patterns,
            "interaction_notes": interactions,
        }
