"""Rule-based claim extraction from AI answers (LLM hook stub for later)."""
from __future__ import annotations

import re
from typing import Any, Callable

from omeia.api.learning_models import ClaimType

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_CITATION_MARKER = re.compile(r"\[\d+\]")
_CLAIM_VERBS = re.compile(
    r"\b(is|are|was|were|shows?|demonstrates?|indicates?|suggests?|associated|correlates?|increases?|decreases?|found|observed|reported)\b",
    re.I,
)
_METHOD_MARKERS = re.compile(r"\b(protocol|workflow|pipeline|method|step|using|performed|analyzed)\b", re.I)
_HYPOTHESIS_MARKERS = re.compile(r"\b(may|might|could|possibly|hypothesi[sz]e|speculat)\b", re.I)


def _classify_claim(sentence: str) -> str:
    if _HYPOTHESIS_MARKERS.search(sentence):
        return ClaimType.HYPOTHESIS.value
    if _METHOD_MARKERS.search(sentence):
        return ClaimType.METHOD.value
    if _CLAIM_VERBS.search(sentence):
        return ClaimType.FACTUAL.value
    return ClaimType.INTERPRETATION.value


def _sentence_has_citation(sentence: str, *, sources: list[dict[str, Any]] | None = None) -> bool:
    if _CITATION_MARKER.search(sentence):
        return True
    if sources:
        lower = sentence.lower()
        for src in sources:
            title = (src.get("title") or "").lower()
            if title and len(title) > 8 and title in lower:
                return True
            doi = (src.get("doi") or "").lower()
            if doi and doi in lower:
                return True
    return False


def extract_claims_rule_based(
    answer_text: str,
    *,
    sources: list[dict[str, Any]] | None = None,
    min_length: int = 40,
) -> list[dict[str, Any]]:
    """Split answer into candidate claims with type and citation flags."""
    text = (answer_text or "").strip()
    if not text:
        return []

    sentences = _SENTENCE_SPLIT.split(text)
    claims: list[dict[str, Any]] = []
    for raw in sentences:
        sentence = raw.strip()
        if len(sentence) < min_length:
            continue
        if sentence.lower().startswith(("i don't", "i do not", "no matching", "i cannot")):
            continue
        has_citation = _sentence_has_citation(sentence, sources=sources)
        claims.append({
            "claim_text": sentence,
            "claim_type": _classify_claim(sentence),
            "has_citation": has_citation,
            "extraction_method": "rule_based",
            "metadata": {"source_count": len(sources or [])},
        })
    return claims


def extract_claims_llm_stub(
    answer_text: str,
    *,
    llm_generate: Callable[[str, str], str] | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Optional LLM extraction hook — falls back to rule-based when unset."""
    if llm_generate is None:
        return extract_claims_rule_based(answer_text, sources=sources)
    # Scaffold: future prompt-based extraction; keep rule-based for reliability.
    return extract_claims_rule_based(answer_text, sources=sources)
