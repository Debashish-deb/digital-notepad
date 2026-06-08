"""Research strategy structured answer schema."""
from __future__ import annotations

from app_skeleton.api.strategy_report_models import (
    RecommendedDirection,
    ResearchStrategyReport,
    StrategyEvidenceRef,
)


def test_strategy_report_schema_roundtrip() -> None:
    report = ResearchStrategyReport(
        executive_summary="Three directions ranked by indexed evidence.",
        recommended_directions=[
            RecommendedDirection(
                title="Spatial TME follow-up",
                rationale="tCyCIF and TLS materials retrieved.",
                internal_evidence=[
                    StrategyEvidenceRef(title="tCyCIF SOP", bucket="lab", snippet="panel workflow"),
                ],
                external_evidence=[
                    StrategyEvidenceRef(title="HGSC spatial review", bucket="research", pmid="12345"),
                ],
                confidence="medium",
                risks=["Cohort heterogeneity"],
                validation_experiments=["Pilot n=10 slides"],
                expected_impact="Improved immune niche mapping",
            )
        ],
        knowledge_gaps=["Limited external literature"],
        confidence_overall="medium",
    )
    data = report.to_public_dict()
    assert data["answer_type"] == "research_strategy"
    assert len(data["recommended_directions"]) == 1
    assert data["recommended_directions"][0]["confidence"] == "medium"
