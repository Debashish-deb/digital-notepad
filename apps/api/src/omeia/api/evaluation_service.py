from __future__ import annotations

from dataclasses import dataclass
from typing import Any

@dataclass
class RetrievalEvalCase:
    query: str
    category: str
    expected_terms: list[str]
    expected_sources: list[str]


def score_retrieval_case(case: RetrievalEvalCase, hits: list[dict[str, Any]]) -> dict[str, Any]:
    combined = "\n".join((h.get("title", "") + " " + h.get("snippet", "") + " " + h.get("source_url", "")) for h in hits).lower()
    found_terms = [term for term in case.expected_terms if term.lower() in combined]
    found_sources = [src for src in case.expected_sources if src.lower() in combined]
    term_score = len(found_terms) / max(1, len(case.expected_terms))
    source_score = len(found_sources) / max(1, len(case.expected_sources)) if case.expected_sources else 1.0
    score = round((term_score * 0.6) + (source_score * 0.4), 3)
    return {
        "query": case.query,
        "category": case.category,
        "score": score,
        "found_terms": found_terms,
        "missing_terms": [t for t in case.expected_terms if t not in found_terms],
        "found_sources": found_sources,
        "result_count": len(hits),
    }

EVAL_CASES = [
    RetrievalEvalCase("MHC class II HGSC spatial tumor ecosystems", "publication", ["MHC", "HGSC", "spatial"], ["Cancer Discovery"]),
    RetrievalEvalCase("tertiary lymphoid structures ovarian cancer CyCIF", "publication", ["TLS", "ovarian", "CyCIF"], []),
    RetrievalEvalCase("GSE211956 Visium HGSOC", "dataset", ["GSE211956", "Visium", "HGSOC"], ["GEO"]),
]
