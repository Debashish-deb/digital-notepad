"""Basic contradiction detection between claims and existing knowledge."""
from __future__ import annotations

import re
from typing import Any

_NEGATION_PAIRS = (
    (re.compile(r"\bincreases?\b", re.I), re.compile(r"\bdecreases?\b", re.I)),
    (re.compile(r"\bpositive\b", re.I), re.compile(r"\bnegative\b", re.I)),
    (re.compile(r"\bassociated with\b", re.I), re.compile(r"\bnot associated with\b", re.I)),
    (re.compile(r"\bpromotes?\b", re.I), re.compile(r"\binhibits?\b", re.I)),
    (re.compile(r"\benhances?\b", re.I), re.compile(r"\bsuppress(es)?\b", re.I)),
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _topic_overlap(a: str, b: str, *, min_tokens: int = 4) -> bool:
    tokens_a = set(re.findall(r"[a-z0-9]{4,}", _normalize(a)))
    tokens_b = set(re.findall(r"[a-z0-9]{4,}", _normalize(b)))
    if not tokens_a or not tokens_b:
        return False
    overlap = tokens_a & tokens_b
    return len(overlap) >= min_tokens


def _polarity_conflict(text_a: str, text_b: str) -> bool:
    for pos_pat, neg_pat in _NEGATION_PAIRS:
        if (pos_pat.search(text_a) and neg_pat.search(text_b)) or (neg_pat.search(text_a) and pos_pat.search(text_b)):
            return True
    explicit_neg = re.compile(r"\b(no|not|never|without)\b", re.I)
    if explicit_neg.search(text_a) != explicit_neg.search(text_b) and _topic_overlap(text_a, text_b, min_tokens=5):
        return True
    return False


def detect_contradictions(
    new_claim: str,
    existing_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return contradiction records against stored knowledge (never silent delete)."""
    conflicts: list[dict[str, Any]] = []
    for item in existing_items:
        status = (item.get("storage_status") or "").upper()
        if status in ("REJECTED", "DEPRECATED"):
            continue
        content = item.get("content") or item.get("title") or ""
        if not _topic_overlap(new_claim, content):
            continue
        if _polarity_conflict(new_claim, content):
            conflicts.append({
                "knowledge_id": str(item.get("knowledge_id") or ""),
                "existing_content": content[:300],
                "new_claim": new_claim[:300],
                "reason": "polarity_conflict",
                "recommended_action": "deprecate_weaker",
            })
    return conflicts


def resolve_contradiction_status(
    new_confidence: float,
    existing_confidence: float,
    existing_status: str,
) -> tuple[str, str]:
    """Decide which item to deprecate — preserve versions, never delete."""
    if new_confidence > existing_confidence + 5:
        return "keep_new", "deprecate_existing"
    if existing_confidence > new_confidence + 5:
        return "deprecate_new", "keep_existing"
    if existing_status == "VERIFIED" and new_confidence < 90:
        return "deprecate_new", "keep_existing"
    return "flag_review", "needs_manual_review"
