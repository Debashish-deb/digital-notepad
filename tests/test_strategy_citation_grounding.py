"""Strategy answers must not invent citations."""
from __future__ import annotations

from omeia.api.evidence_orchestrator import EvidenceItem, EvidencePackage
from omeia.api.research_strategy_engine import _references_from_package


def test_references_only_from_package_items() -> None:
    package = EvidencePackage(
        items=[
            EvidenceItem(
                index=1,
                title="Real paper",
                source_type="publication",
                bucket="research",
                snippet="HGSC study",
                score=0.8,
                pmid="12345678",
            ),
            EvidenceItem(
                index=2,
                title="Internal SOP",
                source_type="protocol",
                bucket="lab",
                snippet="no external id",
                score=0.7,
            ),
        ],
        confidence="medium",
    )
    refs = _references_from_package(package)
    assert len(refs) == 1
    assert refs[0].pmid == "12345678"
    assert refs[0].title == "Real paper"
