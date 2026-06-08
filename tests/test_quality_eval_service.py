"""Unit tests for continuous quality evaluation service."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from omeia.api.quality_eval_service import (
    _compute_composite_score,
    _detect_regressions,
    _resolve_status,
    run_continuous_eval,
)


def test_compute_composite_score_weighted() -> None:
    metrics = {
        "search_qa": {"passed": 10, "failed": 0, "total": 10},
        "copilot": {"release_gates": {"overall_pass_pct": 80}},
        "strategy_engine": {"enabled": True, "passed": 4, "failed": 1},
        "retrieval": {"avg_score": 0.6},
        "feedback": {"positive_rate": 0.5},
    }
    score = _compute_composite_score(metrics)
    assert 50 <= score <= 100


def test_detect_regressions_search_pass_rate() -> None:
    current = {
        "composite_score": 70,
        "metrics": {"search_qa": {"pass_rate": 0.7}},
    }
    previous = {
        "composite_score": 80,
        "metrics": {"search_qa": {"pass_rate": 0.95}},
    }
    regs = _detect_regressions(current, previous)
    assert any(r["metric"] == "search_qa_pass_rate" for r in regs)


def test_resolve_status_fail_on_search_qa(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMEIA_QUALITY_GATE_STRICT", "false")
    status = _resolve_status(
        metrics={"search_qa": {"failed": 2}},
        gates={},
        regressions=[],
    )
    assert status == "fail"


def test_resolve_status_warn_on_gate_without_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMEIA_QUALITY_GATE_STRICT", "false")
    status = _resolve_status(
        metrics={"search_qa": {"failed": 0}},
        gates={"overall_gate_pass": False},
        regressions=[],
    )
    assert status == "warn"


def test_resolve_status_fail_on_gate_with_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMEIA_QUALITY_GATE_STRICT", "true")
    status = _resolve_status(
        metrics={"search_qa": {"failed": 0}},
        gates={"overall_gate_pass": False},
        regressions=[],
    )
    assert status == "fail"


def test_run_continuous_eval_skip_copilot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMEIA_QUALITY_GATE_STRICT", "false")

    search_report = {"passed": 5, "failed": 0, "results": []}
    retrieval_report = {"avg_score": 0.5, "pass": True, "cases": []}
    strategy_report = {"enabled": True, "passed": 3, "failed": 0, "rows": []}
    feedback_report = {"total": 0, "positive_rate": 0}

    with (
        patch("omeia.api.quality_eval_service._run_search_qa", return_value=search_report),
        patch("omeia.api.quality_eval_service._run_retrieval_eval", return_value=retrieval_report),
        patch("omeia.api.quality_eval_service._run_strategy_engine_sample", return_value=strategy_report),
        patch("omeia.api.quality_eval_service._feedback_summary", return_value=feedback_report),
        patch("omeia.api.quality_eval_service.save_eval_run", return_value=None),
        patch("omeia.api.quality_eval_service.fetch_latest_eval_run", return_value=None),
    ):
        report = run_continuous_eval(trigger_source="test", skip_copilot=True, persist=False)

    assert report["status"] in ("pass", "warn")
    assert report["composite_score"] is not None
    assert report["metrics"]["copilot"]["skipped"] is True
    assert report["metrics"]["search_qa"]["passed"] == 5
