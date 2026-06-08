"""Literature trends, citations, and contradictions from indexed publications."""
from __future__ import annotations

import re
from typing import Any

from omeia.api.evidence_orchestrator import EvidencePackage
from omeia.api.strategy_agents._base import EXTERNAL_BUCKETS, filter_items, item_to_ref

PUBLICATION_RE = re.compile(
    r"\b(paper|publication|doi|pmid|journal|cohort|meta-?analysis|review|trial)\b",
    re.I,
)


class LiteratureAgent:
    name = "literature"

    def analyze(self, package: EvidencePackage, *, question: str = "") -> dict[str, Any]:
        items = filter_items(package, buckets=EXTERNAL_BUCKETS, pattern=PUBLICATION_RE, limit=10)
        if not items:
            items = filter_items(package, buckets=EXTERNAL_BUCKETS, limit=6)

        refs = [item_to_ref(i) for i in items]
        trends: list[str] = []
        if len(items) >= 3:
            trends.append(
                f"Multiple indexed publications ({len(items)}) mention themes related to the query."
            )
        elif items:
            trends.append("Limited external literature retrieved — expand research KB indexing.")
        else:
            trends.append("No external literature hits in current retrieval.")

        contradictions: list[str] = []
        for claim in (package.claim_validations or [])[:4]:
            if claim.status == "conflicting":
                contradictions.append(claim.claim[:220])

        return {
            "agent": self.name,
            "external_refs": refs,
            "trends": trends,
            "contradictions": contradictions,
            "citation_count": len(refs),
        }
