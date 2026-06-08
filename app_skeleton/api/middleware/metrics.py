"""Request metrics and structured request_id logging."""
from __future__ import annotations

import logging
import os
import time
import uuid
from collections import defaultdict
from threading import Lock
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

LOGGER = logging.getLogger("omeia.http")

_lock = Lock()
_started_at = time.monotonic()
_request_total = 0
_by_status: dict[str, int] = defaultdict(int)
_by_method: dict[str, int] = defaultdict(int)
_latency_ms_sum = 0.0


def metrics_enabled() -> bool:
    return (os.getenv("ENABLE_REQUEST_METRICS", "false") or "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def snapshot_metrics() -> dict[str, Any]:
    with _lock:
        return {
            "enabled": metrics_enabled(),
            "uptime_seconds": round(time.monotonic() - _started_at, 2),
            "requests_total": _request_total,
            "requests_by_status": dict(sorted(_by_status.items())),
            "requests_by_method": dict(sorted(_by_method.items())),
            "latency_ms_avg": round(_latency_ms_sum / _request_total, 2) if _request_total else 0.0,
        }


def _record(method: str, status_code: int, duration_ms: float) -> None:
    with _lock:
        global _request_total, _latency_ms_sum
        _request_total += 1
        _latency_ms_sum += duration_ms
        _by_status[str(status_code)] += 1
        _by_method[method.upper()] += 1


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Attach request_id, emit structured logs, and update in-memory counters."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = (request.headers.get("x-request-id") or "").strip() or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            LOGGER.exception(
                "request_failed request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            if metrics_enabled():
                _record(request.method, status_code, duration_ms)
            LOGGER.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                request_id,
                request.method,
                request.url.path,
                status_code,
                duration_ms,
            )
