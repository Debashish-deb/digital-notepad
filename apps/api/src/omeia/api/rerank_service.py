"""Cross-encoder style reranking for copilot hits (optional sentence-transformers)."""
from __future__ import annotations

import logging
import os
import re
from typing import Any

LOGGER = logging.getLogger(__name__)

_CROSS_ENCODER = None


def rerank_enabled() -> bool:
    return os.getenv("RERANK_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def _tokenize(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-z0-9\u00c0-\uffff]{3,}", (text or "").lower())
        if t not in {"the", "and", "for", "what", "how", "with", "from", "that", "this"}
    }


def _pair_score(query: str, title: str, snippet: str) -> float:
    q = _tokenize(query)
    if not q:
        return 0.0
    blob = f"{title} {snippet}".lower()
    overlap = sum(1 for tok in q if tok in blob)
    bigram_bonus = 0.0
    words = query.lower().split()
    for i in range(len(words) - 1):
        bg = f"{words[i]} {words[i + 1]}"
        if len(bg) > 5 and bg in blob:
            bigram_bonus += 0.15
    return (overlap / max(len(q), 1)) + bigram_bonus


def _load_cross_encoder():
    global _CROSS_ENCODER
    if _CROSS_ENCODER is not None:
        return _CROSS_ENCODER
    model_name = (os.getenv("RERANK_CROSS_ENCODER_MODEL") or "").strip()
    if not model_name:
        return None
    try:
        from sentence_transformers import CrossEncoder  # type: ignore

        _CROSS_ENCODER = CrossEncoder(model_name)
        return _CROSS_ENCODER
    except Exception as exc:
        LOGGER.warning("CrossEncoder %s unavailable: %s", model_name, exc)
        return None


def rerank_hits(query: str, hits: list[Any], *, top_n: int = 30) -> list[Any]:
    """Rerank SearchHit-like objects; preserves type, updates .score."""
    if not hits or not rerank_enabled():
        return hits[:top_n]

    pool = list(hits[: max(top_n, 30)])
    encoder = _load_cross_encoder()

    if encoder is not None:
        pairs = [
            (query, f"{getattr(h, 'title', '')}: {getattr(h, 'snippet', '')}"[:2000])
            for h in pool
        ]
        try:
            scores = encoder.predict(pairs)
            scored = sorted(zip(scores, pool), key=lambda x: float(x[0]), reverse=True)
            out: list[Any] = []
            for raw_score, hit in scored[:top_n]:
                hit.score = float(raw_score)
                out.append(hit)
            return out
        except Exception as exc:
            LOGGER.warning("CrossEncoder predict failed: %s", exc)

    scored_lex: list[tuple[float, Any]] = []
    for hit in pool:
        base = float(getattr(hit, "score", 0.0) or 0.0)
        pair = _pair_score(query, getattr(hit, "title", "") or "", getattr(hit, "snippet", "") or "")
        scored_lex.append((base * (1.0 + 1.5 * pair), hit))
    scored_lex.sort(key=lambda x: x[0], reverse=True)
    out = []
    for new_score, hit in scored_lex[:top_n]:
        hit.score = new_score
        out.append(hit)
    return out
