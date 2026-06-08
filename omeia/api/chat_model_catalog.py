"""Curated chat model options for the AI Lab Assistant UI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omeia.api.llm_client import LLMClient, _env

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OLLAMA_CATALOG = _REPO_ROOT / "configs" / "ollama_research_models.json"

_GEMINI_UI_MODELS: list[tuple[str, str]] = [
    ("gemini-3.5-flash", "Gemini 3.5 Flash"),
    ("gemini-2.5-flash", "Gemini 2.5 Flash"),
    ("gemini-2.5-pro", "Gemini 2.5 Pro"),
    ("gemini-2.0-flash", "Gemini 2.0 Flash"),
]


def _gemini_models() -> list[dict[str, str]]:
    seen: set[str] = set()
    options: list[dict[str, str]] = []
    for model_id, label in (
        (_env("GEMINI_MODEL", "gemini-3.5-flash"), "Default (env)"),
        (_env("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash"), "Fallback (env)"),
        *_GEMINI_UI_MODELS,
    ):
        mid = (model_id or "").strip()
        if not mid or mid in seen:
            continue
        seen.add(mid)
        display = label if label != "Default (env)" and label != "Fallback (env)" else mid.replace("gemini-", "Gemini ").replace("-", " ")
        options.append({"id": mid, "label": display})
    return options


def _ollama_catalog_models() -> list[dict[str, str]]:
    if not _OLLAMA_CATALOG.is_file():
        return [{"id": _env("OLLAMA_MODEL", "qwen2.5:3b"), "label": _env("OLLAMA_MODEL", "qwen2.5:3b")}]
    try:
        data = json.loads(_OLLAMA_CATALOG.read_text(encoding="utf-8"))
    except Exception:
        return [{"id": _env("OLLAMA_MODEL", "qwen2.5:3b"), "label": _env("OLLAMA_MODEL", "qwen2.5:3b")}]
    options: list[dict[str, str]] = []
    for entry in data.get("models") or []:
        if not entry.get("omeia_chat"):
            continue
        tag = str(entry.get("tag") or "").strip()
        if not tag:
            continue
        use_case = str(entry.get("use_case") or "").replace("_", " ")
        options.append({"id": tag, "label": f"{tag} ({use_case})" if use_case else tag})
    default = str(data.get("default_chat_model") or _env("OLLAMA_MODEL", "qwen2.5:3b"))
    if default and not any(o["id"] == default for o in options):
        options.insert(0, {"id": default, "label": default})
    return options or [{"id": default, "label": default}]


def _provider_healthy(provider: str) -> bool:
    if provider == "mock":
        return True
    if provider == "gemini":
        return bool(_env("GEMINI_API_KEY"))
    probe = LLMClient()
    probe.provider = provider
    if provider == "gemini":
        probe.api_key = _env("GEMINI_API_KEY", "")
        probe.model = _env("GEMINI_MODEL", "gemini-3.5-flash")
        probe.base_url = _env("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    elif provider == "ollama":
        cfg = probe._ollama_endpoint()
        probe.api_key = cfg["api_key"]
        probe.base_url = cfg["base_url"]
        probe.model = _env("OLLAMA_MODEL", "qwen2.5:3b")
    probe._init_client()
    return probe.healthCheck()


def build_chat_model_catalog() -> dict[str, Any]:
    """Return grouped + flat model list for the chat composer picker."""
    chat_provider = _env("CHAT_LLM_PROVIDER", "") or _env("LLM_PROVIDER", "mock")
    default_model = _env("GEMINI_MODEL", "gemini-3.5-flash") if chat_provider == "gemini" else _env("OLLAMA_MODEL", "qwen2.5:3b")

    groups: list[dict[str, Any]] = []
    flat: list[dict[str, Any]] = []

    if _env("GEMINI_API_KEY"):
        gemini_models = _gemini_models()
        healthy = _provider_healthy("gemini")
        groups.append({
            "provider": "gemini",
            "label": "Gemini",
            "healthy": healthy,
            "models": gemini_models,
        })
        for m in gemini_models:
            flat.append({**m, "provider": "gemini", "healthy": healthy, "key": f"gemini:{m['id']}"})

    ollama_models = _ollama_catalog_models()
    ollama_healthy = _provider_healthy("ollama")
    groups.append({
        "provider": "ollama",
        "label": "Ollama (Linux)",
        "healthy": ollama_healthy,
        "models": ollama_models,
    })
    for m in ollama_models:
        flat.append({**m, "provider": "ollama", "healthy": ollama_healthy, "key": f"ollama:{m['id']}"})

    if not flat:
        groups.append({
            "provider": "mock",
            "label": "Mock (offline)",
            "healthy": True,
            "models": [{"id": "mock-model", "label": "Mock model"}],
        })
        flat.append({
            "id": "mock-model",
            "label": "Mock model",
            "provider": "mock",
            "healthy": True,
            "key": "mock:mock-model",
        })
        chat_provider = "mock"
        default_model = "mock-model"

    default_key = f"{chat_provider}:{default_model}"
    if not any(item["key"] == default_key for item in flat) and flat:
        default_key = flat[0]["key"]
        parts = default_key.split(":", 1)
        chat_provider = parts[0]
        default_model = parts[1] if len(parts) > 1 else flat[0]["id"]

    return {
        "default_provider": chat_provider,
        "default_model": default_model,
        "default_key": default_key,
        "groups": groups,
        "options": flat,
    }


def make_chat_llm(
    provider: str | None = None,
    model: str | None = None,
    *,
    default_llm: LLMClient | None = None,
) -> LLMClient:
    """Resolve chat provider/model — UI overrides env defaults per request."""
    base = default_llm or LLMClient()
    chat_provider = (
        (provider or "").strip().lower()
        or _env("CHAT_LLM_PROVIDER", "").strip().lower()
        or base.provider
    ).lower()
    if chat_provider not in LLMClient._KNOWN_PROVIDERS:
        chat_provider = base.provider

    if not provider and not model and not _env("CHAT_LLM_PROVIDER", "").strip():
        return base

    active = LLMClient()
    active.provider = chat_provider

    if chat_provider == "gemini":
        active.api_key = _env("GEMINI_API_KEY", "")
        active.base_url = _env("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
        active.model = (model or _env("GEMINI_MODEL", "gemini-3.5-flash")).strip()
    elif chat_provider == "ollama":
        ollama_cfg = active._ollama_endpoint()
        active.api_key = ollama_cfg["api_key"]
        active.base_url = ollama_cfg["base_url"]
        active.model = (model or _env("OLLAMA_MODEL", "qwen2.5:3b")).strip()
    elif model:
        active.model = model.strip()
        active.api_key = base.api_key
        active.base_url = base.base_url

    active._init_client()
    return active
