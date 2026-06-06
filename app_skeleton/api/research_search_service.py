from __future__ import annotations

import re
from typing import Any

STOPWORDS = {"the", "and", "or", "of", "in", "to", "a", "an", "for", "with", "on"}


def normalize_query(q: str) -> str:
    return " ".join((q or "").strip().split())


def tokenize_query(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9_\-]+", normalize_query(q).lower()) if len(t) > 2 and t not in STOPWORDS]


def keyword_score(title: str, text: str, terms: list[str]) -> float:
    if not terms:
        return 0.0
    title_l = (title or "").lower()
    text_l = (text or "").lower()
    score = 0.0
    for term in terms:
        if term in title_l:
            score += 2.0
        if term in text_l:
            score += 1.0
    return min(1.0, score / max(1.0, len(terms) * 2.0))


def make_snippet(text: str, terms: list[str], max_chars: int = 420) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return text
    lower = text.lower()
    first = min([lower.find(t) for t in terms if lower.find(t) >= 0] or [0])
    start = max(0, first - max_chars // 3)
    return ("…" if start else "") + text[start:start + max_chars] + "…"


def merge_scores(semantic_score: float, kw_score: float, source_priority: float = 0.0) -> float:
    return round((semantic_score * 0.58) + (kw_score * 0.32) + (source_priority * 0.10), 5)


def build_research_nav(hit: dict[str, Any]) -> dict[str, Any]:
    source_type = hit.get("source_type") or "research"
    if source_type == "dataset":
        return {"main": "ai_assistant", "sub": "research_kb", "dataset_accession": hit.get("dataset_accession")}
    if source_type in {"publication", "preprint", "publication_metadata"}:
        return {"main": "ai_assistant", "sub": "research_kb", "source_url": hit.get("source_url"), "doi": hit.get("doi")}
    return {"main": "ai_assistant", "sub": "research_kb", "source_url": hit.get("source_url")}


def normalize_research_hit(raw: dict[str, Any], query_terms: list[str]) -> dict[str, Any]:
    title = raw.get("title") or "Untitled"
    text = raw.get("snippet") or raw.get("text") or ""
    kw = keyword_score(title, text, query_terms)
    semantic = float(raw.get("score") or 0.0)
    source_priority = 1.0 if (raw.get("metadata") or {}).get("lab_priority") else 0.0
    score = merge_scores(semantic, kw, source_priority)
    return {
        "id": str(raw.get("id") or raw.get("source_id") or title),
        "bucket": "research",
        "title": title,
        "snippet": make_snippet(text, query_terms),
        "score": score,
        "source_url": raw.get("source_url"),
        "source_type": raw.get("source_type"),
        "doi": raw.get("doi"),
        "pmid": raw.get("pmid"),
        "dataset_accession": raw.get("dataset_accession"),
        "entities": raw.get("entities") or [],
        "nav": build_research_nav(raw),
        "metadata": raw.get("metadata") or {},
    }
