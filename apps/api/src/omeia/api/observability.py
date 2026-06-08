"""Structured timing records for startup phases and hot API paths."""
from __future__ import annotations

import logging
import os
import time
from threading import Lock
from typing import Any

LOGGER = logging.getLogger("omeia.timing")

_lock = Lock()
_timings: dict[str, list[float]] = {}


def observability_enabled() -> bool:
    return os.getenv("ENABLE_OBSERVABILITY", "true").strip().lower() in ("1", "true", "yes", "on")


def record_timing(phase: str, duration_ms: float, **extra: Any) -> None:
    """Log a structured timing line and accumulate for /metrics when enabled."""
    if not observability_enabled():
        return
    phase_key = (phase or "unknown").strip()
    with _lock:
        _timings.setdefault(phase_key, []).append(float(duration_ms))
    payload = {"phase": phase_key, "duration_ms": round(float(duration_ms), 2), **extra}
    LOGGER.info("timing %s", payload)


class timed:
    """Context manager: record elapsed ms for a named phase."""

    def __init__(self, phase: str, **extra: Any) -> None:
        self.phase = phase
        self.extra = extra
        self._start = 0.0

    def __enter__(self) -> "timed":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        duration_ms = (time.perf_counter() - self._start) * 1000.0
        record_timing(self.phase, duration_ms, **self.extra)


record_phase = timed


def snapshot_timings() -> dict[str, Any]:
    with _lock:
        summary: dict[str, Any] = {}
        for phase, samples in sorted(_timings.items()):
            if not samples:
                continue
            summary[phase] = {
                "count": len(samples),
                "total_ms": round(sum(samples), 2),
                "avg_ms": round(sum(samples) / len(samples), 2),
                "last_ms": round(samples[-1], 2),
            }
        return summary


timing_snapshot = snapshot_timings
