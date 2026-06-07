"""Lightweight per-user and per-IP rate limiting for copilot/chat endpoints."""
from __future__ import annotations

import os
import time
from collections import defaultdict
from threading import Lock
from typing import Any

_LOCK = Lock()
_BUCKETS: dict[str, list[float]] = defaultdict(list)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _limit_per_minute() -> int:
    return max(1, _env_int("COPILOT_RATE_LIMIT_PER_MINUTE", 30))


def _window_seconds() -> int:
    return max(30, _env_int("COPILOT_RATE_LIMIT_WINDOW_SEC", 60))


def _prune(timestamps: list[float], *, now: float, window: float) -> list[float]:
    cutoff = now - window
    return [t for t in timestamps if t >= cutoff]


def check_rate_limit(
    *,
    user_id: str | None = None,
    ip_address: str | None = None,
) -> tuple[bool, dict[str, str]]:
    """Return (allowed, headers) for X-RateLimit-* response headers."""
    limit = _limit_per_minute()
    window = float(_window_seconds())
    now = time.time()
    keys: list[str] = []
    if user_id:
        keys.append(f"user:{user_id}")
    if ip_address:
        keys.append(f"ip:{ip_address}")
    if not keys:
        keys.append("anon:global")

    with _LOCK:
        remaining = limit
        reset_at = int(now + window)
        for key in keys:
            bucket = _prune(_BUCKETS[key], now=now, window=window)
            _BUCKETS[key] = bucket
            used = len(bucket)
            remaining = min(remaining, max(0, limit - used))
            if used >= limit:
                oldest = bucket[0] if bucket else now
                reset_at = int(oldest + window)
                headers = {
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                }
                return False, headers

        for key in keys:
            _BUCKETS[key].append(now)

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, remaining - 1)),
            "X-RateLimit-Reset": str(reset_at),
        }
        return True, headers


def apply_rate_limit_headers(response: Any, headers: dict[str, str]) -> None:
    for key, value in headers.items():
        response.headers[key] = value
