"""Phase A/B copilot enhancement unit tests."""
from __future__ import annotations

from types import SimpleNamespace

from omeia.api.chat_service import _needs_evidence_regen
from omeia.api.embedding_service import embed_text, hash_embed, embedding_dim
from omeia.api.evidence_orchestrator import ClaimValidation, EvidencePackage, EvidenceItem
from omeia.api.rerank_service import rerank_hits, _pair_score
from omeia.api.search_models import SearchHit


def test_hash_embed_normalized():
    a = hash_embed("EyeMT GeoMx spatial transcriptomics", dim=64)
    b = hash_embed("EyeMT GeoMx spatial transcriptomics", dim=64)
    assert len(a) == 64
    assert a == b
    norm = sum(x * x for x in a) ** 0.5
    assert abs(norm - 1.0) < 0.01


def test_embed_text_offline_fallback():
    vec = embed_text("HGSC tertiary lymphoid structures")
    assert len(vec) >= 32
    assert abs(sum(v * v for v in vec) ** 0.5 - 1.0) < 0.05


def test_pair_score_boosts_overlap():
    low = _pair_score("EyeMT project", "Unrelated", "Nothing here")
    high = _pair_score("EyeMT project", "EyeMT slidedeck", "GeoMx progress for EyeMT project")
    assert high > low


def test_rerank_hits_reorders():
    hits = [
        SearchHit(id="1", bucket="research", title="Paper", snippet="ovarian cancer unrelated", score=0.4),
        SearchHit(id="2", bucket="file", title="EyeMT deck", snippet="EyeMT GeoMx project overview", score=0.4),
    ]
    out = rerank_hits("tell me about EyeMT project", hits, top_n=2)
    assert out[0].id == "2"
    assert out[0].score >= out[1].score


def test_needs_evidence_regen_conflicting():
    pkg = EvidencePackage(
        items=[],
        claim_validations=[
            ClaimValidation(claim="TLS improves survival", status="conflicting", supporting_indices=(1, 2)),
        ],
        confidence="medium",
    )
    assert _needs_evidence_regen(pkg) is True


def test_needs_evidence_regen_low_confidence():
    pkg = EvidencePackage(items=[], claim_validations=[], confidence="insufficient")
    assert _needs_evidence_regen(pkg) is True


def test_needs_evidence_regen_ok():
    pkg = EvidencePackage(
        items=[EvidenceItem(1, "t", "lab", "lab", "snippet", 0.8)],
        claim_validations=[
            ClaimValidation(claim="supported", status="corroborated", supporting_indices=(1,)),
        ],
        confidence="high",
    )
    assert _needs_evidence_regen(pkg) is False


def test_format_memory_block():
    from omeia.api.chat_session_store import SessionContext, format_memory_block

    ctx = SessionContext(
        session_id="abc",
        summary="User asked about EyeMT GeoMx.",
        recent_turns=(("user", "What is EyeMT?"), ("assistant", "EyeMT integrates GeoMx.")),
    )
    block = format_memory_block(ctx)
    assert "EyeMT" in block
    assert "Recent turns" in block
