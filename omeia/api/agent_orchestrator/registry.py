"""Load agent category and internal agent registries."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from omeia._repo import find_repo_root

_REPO = find_repo_root()
_CATEGORIES = _REPO / "configs" / "agent_categories.json"
_AGENTS = _REPO / "configs" / "internal_agents.json"


@lru_cache(maxsize=1)
def load_categories_config() -> dict[str, Any]:
    return json.loads(_CATEGORIES.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_agents_config() -> dict[str, Any]:
    return json.loads(_AGENTS.read_text(encoding="utf-8"))


def list_visible_categories() -> list[dict[str, Any]]:
    cfg = load_categories_config()
    modes = {m["id"]: m for m in cfg.get("modes", [])}
    out: list[dict[str, Any]] = []
    for cid, cat in (cfg.get("categories") or {}).items():
        if not cat.get("visible", True):
            continue
        out.append({
            "id": cid,
            "label": cat.get("label"),
            "description": cat.get("description"),
            "icon": cat.get("icon"),
            "default_mode": cat.get("default_mode") or cfg.get("default_mode", "balanced"),
            "team_preview": cat.get("team_preview") or [],
            "modes": list(modes.values()),
        })
    return out


def get_category(category_id: str) -> dict[str, Any] | None:
    cfg = load_categories_config()
    cat = (cfg.get("categories") or {}).get(category_id)
    if not cat:
        return None
    return {"id": category_id, **cat}


def agents_for_category(category_id: str, mode: str) -> list[str]:
    cat = get_category(category_id)
    if not cat:
        return []
    agents_map = cat.get("agents") or {}
    return list(agents_map.get(mode) or agents_map.get("balanced") or [])


def get_agent(agent_id: str) -> dict[str, Any] | None:
    agents = (load_agents_config().get("agents") or {})
    spec = agents.get(agent_id)
    if not spec:
        return None
    return {"id": agent_id, **spec}


def _friendly_model_name(provider: str | None, model: str | None) -> str:
    raw = (model or "").strip()
    if not raw:
        return "Auto"
    base = raw.split(":")[0].lower()
    aliases = {
        "medgemma": "MedGemma",
        "meditron": "Meditron",
        "medllama2": "MedLLaMA2",
        "qwen2.5": "Qwen 2.5",
        "llama3.1": "Llama 3.1",
        "llama3.2": "Llama 3.2",
        "mistral-nemo": "Mistral Nemo",
        "gemini-2.5-flash": "Gemini Flash",
        "gemini-3.5-flash": "Gemini Flash",
        "phi3": "Phi-3",
    }
    label = aliases.get(base, base.replace("-", " ").title())
    if provider == "gemini" and "gemini" not in label.lower():
        return f"Gemini · {label}"
    if provider == "ollama":
        return label
    return f"{(provider or 'model').title()} · {label}"


def _agent_chains(agent: dict[str, Any]) -> list[str]:
    chains: list[str] = []
    role = agent.get("role")
    if role == "planner":
        chains.append("Planner")
    if agent.get("use_rag"):
        chains.extend(["RAG", "Lab KB"])
    if agent.get("safety") == "biomedical":
        chains.append("Evidence")
    if role == "synthesizer":
        chains.append("Synthesis")
    if not chains:
        chains.append("Reasoning")
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for item in chains:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def team_roster_for_category(category_id: str, mode: str) -> list[dict[str, Any]]:
    roster: list[dict[str, Any]] = []
    for aid in agents_for_category(category_id, mode):
        agent = get_agent(aid)
        if not agent:
            continue
        pref = agent.get("preferred_model") or {}
        fb = agent.get("fallback_model") or {}
        roster.append({
            "id": aid,
            "label": agent.get("label") or aid,
            "role": agent.get("role"),
            "model": _friendly_model_name(pref.get("provider"), pref.get("model")),
            "fallback_model": _friendly_model_name(fb.get("provider"), fb.get("model")),
            "chains": _agent_chains(agent),
            "specialty": (agent.get("specialty") or "")[:120],
        })
    return roster


def public_category_detail(category_id: str, mode: str | None = None) -> dict[str, Any] | None:
    cat = get_category(category_id)
    if not cat:
        return None
    active_mode = mode or cat.get("default_mode", "balanced")
    team = []
    for aid in agents_for_category(category_id, active_mode):
        agent = get_agent(aid)
        if agent and agent.get("role") != "synthesizer":
            team.append(agent.get("label") or aid)
    return {
        "id": category_id,
        "label": cat.get("label"),
        "description": cat.get("description"),
        "icon": cat.get("icon"),
        "default_mode": cat.get("default_mode"),
        "mode": active_mode,
        "team_preview": cat.get("team_preview") or team,
        "team_roster": team_roster_for_category(category_id, active_mode),
        "modes": load_categories_config().get("modes", []),
    }
