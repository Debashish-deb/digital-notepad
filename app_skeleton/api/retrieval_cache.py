"""In-memory retrieval-result cache for unified search (not final LLM answers)."""
from __future__ import annotations

import hashlib
import json
import os
import time
from threading import Lock
from typing import Any

_LOCK = Lock()
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def cache_enabled() -> bool:
    return os.getenv("RETRIEVAL_CACHE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def cache_ttl_seconds() -> int:
    return max(5, _env_int("RETRIEVAL_CACHE_TTL_SEC", 120))


def cache_max_entries() -> int:
    return max(16, _env_int("RETRIEVAL_CACHE_MAX_ENTRIES", 256))


def make_cache_key(
    *,
    query: str,
    scopes: str | None,
    mode: str,
    user_id: str | None,
    user_role: str | None,
    project_codes: list[str] | None,
    filters: dict[str, Any] | None,
    include_restricted: bool,
) -> str:
    payload = {
        "q": (query or "").strip().lower(),
        "scopes": scopes or "",
        "mode": mode,
        "user": user_id or "",
        "role": user_role or "",
        "projects": sorted(project_codes or []),
        "filters": filters or {},
        "restricted": include_restricted,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return digest[:32]


def should_cache(*, include_restricted: bool, user_role: str | None, hits: list[dict[str, Any]] | None = None) -> bool:
    if not cache_enabled():
        return False
    if include_restricted:
        return False
    if (user_role or "").lower() not in {"", "viewer", "researcher", "editor", "admin"}:
        return False
    for hit in hits or []:
        level = (hit.get("visibility_level") or "").lower()
        if level in {"restricted", "confidential"}:
            return False
    return True


def get_cached(key: str) -> dict[str, Any] | None:
    if not cache_enabled():
        return None
    now = time.time()
    with _LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None
        expires, payload = entry
        if expires < now:
            _CACHE.pop(key, None)
            return None
        return dict(payload)


def set_cached(key: str, payload: dict[str, Any]) -> None:
    if not cache_enabled():
        return
    ttl = cache_ttl_seconds()
    max_entries = cache_max_entries()
    expires = time.time() + ttl
    with _LOCK:
        if len(_CACHE) >= max_entries:
            oldest = min(_CACHE.items(), key=lambda item: item[1][0])[0]
            _CACHE.pop(oldest, None)
        _CACHE[key] = (expires, dict(payload))


def clear_cache() -> None:
    with _LOCK:
        _CACHE.clear()


def copilot_cache_ttl_seconds() -> int:
    return max(5, _env_int("COPILOT_RETRIEVAL_CACHE_TTL_SEC", 90))


def make_copilot_cache_key(
    *,
    query: str,
    intent: str | None,
    project_codes: list[str] | None,
    user_role: str | None,
    include_restricted: bool,
    limit: int,
) -> str:
    payload = {
        "kind": "copilot_hits",
        "q": (query or "").strip().lower(),
        "intent": intent or "",
        "projects": sorted(project_codes or []),
        "role": user_role or "",
        "restricted": include_restricted,
        "limit": limit,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return f"copilot:{digest[:32]}"


def get_copilot_cached(key: str) -> list[dict[str, Any]] | None:
    if not cache_enabled() or os.getenv("COPILOT_RETRIEVAL_CACHE_ENABLED", "true").strip().lower() not in {
        "1", "true", "yes", "on",
    }:
        return None
    now = time.time()
    with _LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None
        expires, payload = entry
        if expires < now:
            _CACHE.pop(key, None)
            return None
        hits = payload.get("hits")
        if not isinstance(hits, list):
            return None
        return list(hits)


def set_copilot_cached(key: str, hits: list[dict[str, Any]]) -> None:
    if not cache_enabled() or os.getenv("COPILOT_RETRIEVAL_CACHE_ENABLED", "true").strip().lower() not in {
        "1", "true", "yes", "on",
    }:
        return
    ttl = copilot_cache_ttl_seconds()
    expires = time.time() + ttl
    with _LOCK:
        if len(_CACHE) >= cache_max_entries():
            oldest = min(_CACHE.items(), key=lambda item: item[1][0])[0]
            _CACHE.pop(oldest, None)
        _CACHE[key] = (expires, {"hits": list(hits)})
