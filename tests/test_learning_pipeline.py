"""Learning pipeline unit tests (claim extraction, contradiction, graph)."""
from __future__ import annotations

from omeia.api.claim_extractor import extract_claims_rule_based
from omeia.api.contradiction_checker import detect_contradictions, resolve_contradiction_status
from omeia.api.confidence_scorer import storage_status_from_confidence
from omeia.api.knowledge_graph_service import extract_graph_from_text, map_entity_type
from omeia.api.learning_models import StorageStatus


def test_extract_claims_finds_factual_sentence() -> None:
    answer = (
        "MHC class II expression is associated with improved outcomes in HGSC patients. "
        "Short note."
    )
    claims = extract_claims_rule_based(
        answer,
        sources=[{"title": "HGSC spatial atlas", "doi": "10.1234/example"}],
    )
    assert len(claims) >= 1
    assert any("MHC class II" in c["claim_text"] for c in claims)


def test_claim_citation_marker_detected() -> None:
    answer = "TLS density correlates with survival in ovarian cancer cohorts [1]."
    claims = extract_claims_rule_based(answer)
    assert claims
    assert claims[0]["has_citation"] is True


def test_contradiction_detects_polarity_conflict() -> None:
    existing = [{
        "knowledge_id": "aaa",
        "storage_status": "VERIFIED",
        "content": "Drug X increases TLS formation in HGSC tumors.",
        "confidence_score": 85,
    }]
    conflicts = detect_contradictions(
        "Drug X decreases TLS formation in HGSC tumors significantly.",
        existing,
    )
    assert conflicts
    assert conflicts[0]["reason"] == "polarity_conflict"


def test_resolve_contradiction_deprecates_weaker() -> None:
    action, _ = resolve_contradiction_status(92.0, 70.0, "DRAFT")
    assert action == "keep_new"


def test_map_entity_type_maps_disease() -> None:
    assert map_entity_type("disease") == "cancer_type"


def test_graph_extraction_returns_edges(monkeypatch) -> None:
    monkeypatch.setattr(
        "omeia.api.knowledge_graph_service.insert_graph_edge",
        lambda **kwargs: "edge-1",
    )
    edges = extract_graph_from_text(
        "TLS occurs in HGSC tumor microenvironment with MHC class II markers.",
        knowledge_id="kid-1",
        storage_status=StorageStatus.DRAFT.value,
        confidence_score=70.0,
    )
    assert edges
    assert any(e["relation_type"] for e in edges)


def test_storage_status_low_confidence_band() -> None:
    status = storage_status_from_confidence(55.0, has_citation=True)
    assert status == StorageStatus.LOW_CONFIDENCE
