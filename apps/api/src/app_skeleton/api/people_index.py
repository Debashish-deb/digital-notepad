"""Searchable lab member directory — backed by configs/lab_people_index.json."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app_skeleton.api.paths import REPO_ROOT

PEOPLE_INDEX_PATH = REPO_ROOT / "configs" / "lab_people_index.json"


def _load_people() -> list[dict[str, Any]]:
    if not PEOPLE_INDEX_PATH.is_file():
        return []
    try:
        data = json.loads(PEOPLE_INDEX_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("people", [])
    except (json.JSONDecodeError, OSError):
        return []


def _score_person(query: str, person: dict[str, Any]) -> float:
    q = query.lower().strip()
    if not q:
        return 0.0
    blob = " ".join(
        str(person.get(k) or "")
        for k in ("full_name", "username", "role", "bio", "research_interests", "affiliation")
    ).lower()
    if not blob:
        return 0.0
    tokens = [t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{2,}", q) if len(t) > 1]
    if not tokens:
        return 0.0
    overlap = sum(1 for t in tokens if t in blob)
    if overlap == 0:
        return 0.0
    return min(1.0, 0.35 + 0.15 * overlap)


def search_people(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Keyword search over the lab people index."""
    people = _load_people()
    scored: list[tuple[float, dict[str, Any]]] = []
    for person in people:
        score = _score_person(query, person)
        if score > 0:
            scored.append((score, person))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    hits: list[dict[str, Any]] = []
    for score, person in scored[:limit]:
        interests = person.get("research_interests") or person.get("skills") or []
        if isinstance(interests, list):
            interests_text = ", ".join(str(x) for x in interests[:6])
        else:
            interests_text = str(interests)
        snippet = (
            f"{person.get('role', '')}. {person.get('bio', '')[:400]} "
            f"Research interests: {interests_text}"
        ).strip()
        hits.append({
            "id": person.get("username") or person.get("full_name"),
            "title": person.get("full_name") or person.get("username"),
            "snippet": snippet[:1200],
            "score": score,
            "source_type": "lab_member",
            "username": person.get("username"),
            "role": person.get("role"),
            "email": person.get("email"),
            "profile_url": person.get("profile_url"),
            "orcid": person.get("orcid"),
            "provenance": person.get("provenance") or "lab_people_index",
        })
    return hits
