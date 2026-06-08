"""Strategy agent unit tests."""
from __future__ import annotations

from app_skeleton.api.evidence_orchestrator import EvidenceItem, EvidencePackage
from app_skeleton.api.strategy_agents import (
    BiomarkerAgent,
    ExperimentalDesignAgent,
    LiteratureAgent,
    ResearchGapAgent,
    SpatialBiologyAgent,
)


def _package() -> EvidencePackage:
    items = [
        EvidenceItem(
            index=1,
            title="tCyCIF TLS protocol",
            source_type="protocol",
            bucket="lab",
            snippet="spatial tme tls tcycif multiplex panel",
            score=0.9,
        ),
        EvidenceItem(
            index=2,
            title="TIM-3 HGSC publication",
            source_type="publication",
            bucket="research",
            snippet="biomarker TIM-3 PD-L1 ovarian cohort",
            score=0.82,
            pmid="9999999",
        ),
    ]
    return EvidencePackage(
        items=items,
        by_bucket={"lab": 1, "research": 1},
        confidence="medium",
        cross_source_summary="2 sources across lab and research",
    )


def test_literature_agent_finds_external_refs() -> None:
    out = LiteratureAgent().analyze(_package())
    assert out["citation_count"] >= 1


def test_biomarker_agent_suggestions() -> None:
    out = BiomarkerAgent().analyze(_package())
    assert out["internal_refs"] or out["marker_suggestions"]


def test_spatial_agent_patterns() -> None:
    out = SpatialBiologyAgent().analyze(_package())
    assert out["spatial_patterns"]


def test_gap_agent_lists_gaps() -> None:
    pkg = EvidencePackage(items=[], confidence="insufficient")
    out = ResearchGapAgent().analyze(pkg)
    assert out["knowledge_gaps"]


def test_experimental_design_feasibility() -> None:
    out = ExperimentalDesignAgent().analyze(_package())
    assert out["experiments"]
    assert out["feasibility"] in {"low", "medium", "high"}
