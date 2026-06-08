"""Conversational retrieval query expansion tests."""
from __future__ import annotations

from omeia.api.chat_query_expansion import (
    build_contextual_retrieval_query,
    enrich_query_with_library_scope,
)
from omeia.api.chat_session_store import SessionContext
from omeia.api.evidence_orchestrator import apply_category_search_boost, build_search_plan
from omeia.api.chat_intent import IntentDecision


def test_expand_follow_up_with_session_context():
    ctx = SessionContext(
        session_id="s1",
        summary="",
        recent_turns=(
            ("user", "What CycIF panel does TLS use?"),
            ("assistant", "TLS cohorts use a 32-marker CycIF panel including CD3 and CD20."),
        ),
    )
    query, note = build_contextual_retrieval_query("tell me more about gating", session_ctx=ctx)
    assert note == "conversation_context"
    assert "CycIF panel" in query
    assert "gating" in query


def test_tell_me_more_about_source_title():
    query, note = build_contextual_retrieval_query("Tell me more about: Ashlar stitching protocol")
    assert note == "source_follow_up"
    assert query == "Ashlar stitching protocol"


def test_library_scope_enrichment():
    out = enrich_query_with_library_scope(
        "staining workflow",
        {"scope_label": "Lab Operations", "domain_tab": "wet_lab"},
    )
    assert "Lab Operations" in out
    assert "wet_lab" in out


def test_category_boost_prioritizes_protocol_buckets():
    intent = IntentDecision(
        intent="protocol_question",
        use_rag=True,
        show_sources=True,
        require_citations=True,
        answer_style="scientific_with_sources",
        reason="test",
    )
    plan = build_search_plan(intent, ("protocols_pipelines",), (), agent_category="wet_lab_cycif")
    assert plan.prioritize_buckets[0] == "lab"
    assert "document_library" in plan.prioritize_buckets
