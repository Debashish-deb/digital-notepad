"""Shared helpers for strategy agents."""
from __future__ import annotations

import re
from typing import Any

from omeia.api.evidence_orchestrator import EvidenceItem, EvidencePackage
from omeia.api.strategy_report_models import StrategyEvidenceRef

INTERNAL_BUCKETS = frozenset({
    "lab",
    "file",
    "vault",
    "document_library",
    "notebook",
    "wiki",
    "project",
    "people",
})

EXTERNAL_BUCKETS = frozenset({"research"})


def item_to_ref(item: EvidenceItem) -> StrategyEvidenceRef:
    return StrategyEvidenceRef(
        title=item.title,
        source_type=item.source_type,
        bucket=item.bucket,
        snippet=(item.snippet or "")[:600],
        doi=item.doi,
        pmid=item.pmid,
        source_url=item.source_url,
        evidence_index=item.index,
    )


def filter_items(
    package: EvidencePackage,
    *,
    buckets: frozenset[str] | None = None,
    pattern: re.Pattern[str] | None = None,
    limit: int = 8,
) -> list[EvidenceItem]:
    out: list[EvidenceItem] = []
    for item in package.items:
        if buckets and item.bucket not in buckets:
            continue
        blob = f"{item.title} {item.snippet}".lower()
        if pattern and not pattern.search(blob):
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out


def agent_notes(package: EvidencePackage, label: str) -> dict[str, Any]:
    return {
        "agent": label,
        "evidence_count": len(package.items),
        "confidence": package.confidence,
    }
