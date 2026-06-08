"""Research Strategy Engine workflow."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from omeia.api.chat_conversation import classify_and_enrich
from omeia.api.evidence_orchestrator import EvidenceItem, EvidencePackage
from omeia.api.research_strategy_engine import (
    INSUFFICIENT_MESSAGE,
    ResearchStrategyEngine,
    is_strategy_question,
)


class _FakeHit:
    def __init__(self, **kwargs: object) -> None:
        self.__dict__.update(kwargs)

    def model_dump(self) -> dict:
        return dict(self.__dict__)


def test_is_strategy_question_detects_planning() -> None:
    assert is_strategy_question(
        "What are the three strongest directions for our next ovarian cancer study?"
    )
    assert not is_strategy_question("What is the weather today?")


def test_engine_insufficient_evidence_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMEIA_STRATEGY_REPORT_MODE", "true")
    monkeypatch.setenv("OMEIA_STRATEGY_REQUIRE_CITATIONS", "true")

    search_svc = MagicMock()
    search_svc.hits_for_copilot.return_value = []

    def _fake_package(*_a, **_k):
        return EvidencePackage(items=[], confidence="insufficient")

    monkeypatch.setattr(
        "omeia.api.research_strategy_engine.package_evidence",
        _fake_package,
    )

    message = "What should we investigate next in HGSC spatial biology?"
    intent = classify_and_enrich(message)
    engine = ResearchStrategyEngine(search_svc)
    result = engine.run(message, intent_decision=intent)

    assert result["research_strategy"] is True
    assert INSUFFICIENT_MESSAGE in result["strategy_report"]["executive_summary"]
    assert result["strategy_report"]["answer_type"] == "research_strategy"


def test_engine_produces_directions_with_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMEIA_STRATEGY_REPORT_MODE", "true")

    hits = [
        _FakeHit(
            id="h1",
            title="tCyCIF panel SOP",
            snippet="spatial TLS immune multiplex tCyCIF",
            bucket="lab",
            score=0.9,
            source_type="protocol",
            metadata={},
        ),
        _FakeHit(
            id="h2",
            title="HGSC biomarker TIM-3",
            snippet="biomarker PD-L1 TIM-3 HGSC",
            bucket="research",
            score=0.85,
            source_type="publication",
            metadata={"pmid": "9999999"},
        ),
    ]
    search_svc = MagicMock()
    search_svc.hits_for_copilot.return_value = hits

    from omeia.api.evidence_orchestrator import package_evidence as real_package

    monkeypatch.setattr(
        "omeia.api.research_strategy_engine.package_evidence",
        real_package,
    )

    message = "Which biomarkers and spatial experiments are highest value for our next study?"
    intent = classify_and_enrich(message)
    engine = ResearchStrategyEngine(search_svc)
    result = engine.run(message, intent_decision=intent)

    report = result["strategy_report"]
    assert report["answer_type"] == "research_strategy"
    assert len(report["recommended_directions"]) >= 1
    assert result["synthesis_mode"] == "research_strategy"
