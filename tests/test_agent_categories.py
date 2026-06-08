"""Tests for category-based agent orchestration."""
from __future__ import annotations

import inspect

import pytest

from omeia.api.agent_orchestrator.registry import (
    agents_for_category,
    get_agent,
    list_visible_categories,
    public_category_detail,
)


def test_visible_categories_exclude_raw_models():
    cats = list_visible_categories()
    assert len(cats) >= 8
    labels = [c["label"] for c in cats]
    assert "Oncology & Tumor Microenvironment" in labels
    assert "Platform & Pipeline Engineering" in labels
    for cat in cats:
        assert "qwen" not in cat["label"].lower()
        assert "gemini" not in cat["label"].lower()


def test_cancer_category_agents_only_oncology_team():
    agents = agents_for_category("cancer_oncology", "balanced")
    assert "oncology_reasoner" in agents
    assert "software_architect" not in agents
    assert "backend_agent" not in agents
    assert "synthesizer" in agents


def test_code_category_uses_software_agents():
    agents = agents_for_category("platform_engineering", "balanced")
    assert "software_architect" in agents
    assert "backend_agent" in agents
    assert "oncology_reasoner" not in agents


def test_fast_mode_single_primary_agent():
    agents = agents_for_category("cancer_oncology", "fast")
    assert agents == ["oncology_reasoner"]


def test_internal_agents_have_model_mapping_hidden():
    agent = get_agent("oncology_reasoner")
    assert agent is not None
    assert agent["preferred_model"]["provider"] == "ollama"
    assert "med" in agent["preferred_model"]["model"]


def test_category_detail_has_team_preview():
    detail = public_category_detail("spatial_multiplex")
    assert detail is not None
    assert detail["label"] == "Spatial & Multiplex Imaging"
    assert detail.get("team_preview")


def test_category_detail_includes_team_roster_with_models():
    detail = public_category_detail("cancer_oncology", "balanced")
    assert detail is not None
    roster = detail.get("team_roster") or []
    assert roster
    assert roster[0].get("model")
    assert roster[0].get("chains")


def test_agent_category_run_route_signature() -> None:
    """Duplicate /run route must accept Request/Response like /api/chat/category."""
    from omeia.api.routers import agent_categories

    run_fn = agent_categories.run_category
    sig = inspect.signature(run_fn)
    assert "request" in sig.parameters
    assert "response" in sig.parameters
    assert "user" in sig.parameters

    execute_fn = agent_categories._execute_category_chat
    sig2 = inspect.signature(execute_fn)
    assert set(sig2.parameters) >= {"req", "request", "response", "user"}
