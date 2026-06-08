"""In-memory agent run traces (debug / advanced mode).

Production note: traces live in this process only (max 200 entries). Restarts and
multi-worker setups do not share trace history; use AGENT_AUDIT_PERSIST when durable
audit is required.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

_TRACES: dict[str, dict[str, Any]] = {}
_MAX_TRACES = 200


def create_trace(*, category: str, mode: str) -> dict[str, Any]:
    trace = {
        "run_id": str(uuid.uuid4()),
        "category": category,
        "mode": mode,
        "agents_started": [],
        "agents_skipped": [],
        "models_used": [],
        "tool_calls": [],
        "intermediate_outputs": [],
        "warnings": [],
        "started_at": time.time(),
        "latency_ms": 0,
    }
    _TRACES[trace["run_id"]] = trace
    if len(_TRACES) > _MAX_TRACES:
        oldest = next(iter(_TRACES))
        _TRACES.pop(oldest, None)
    return trace


def get_trace(run_id: str) -> dict[str, Any] | None:
    return _TRACES.get(run_id)


def finalize_trace(
    trace: dict[str, Any],
    *,
    db_conn: str | None = None,
    source_buckets: list[str] | None = None,
    source_counts: dict[str, int] | None = None,
    provider: str | None = None,
    model: str | None = None,
    grounding_outcome: str | None = None,
    user_email: str | None = None,
    user_role: str | None = None,
) -> None:
    trace["latency_ms"] = int((time.time() - trace.get("started_at", time.time())) * 1000)
    if db_conn:
        try:
            from omeia.api.agent_orchestrator.persistent_audit import persist_agent_audit

            persist_agent_audit(
                trace,
                db_conn=db_conn,
                source_buckets=source_buckets,
                source_counts=source_counts,
                provider=provider,
                model=model,
                grounding_outcome=grounding_outcome,
                user_email=user_email,
                user_role=user_role,
            )
        except Exception:
            pass
