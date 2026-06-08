"""Optional persistent audit logging for agent runs — append-only, redacted."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import psycopg

LOGGER = logging.getLogger(__name__)

_PATIENT_PATTERNS = (
    re.compile(r"\bMRN[:\s#-]*\d{4,}\b", re.I),
    re.compile(r"\bpatient[_\s-]?id[:\s#-]*[A-Z0-9]{6,}\b", re.I),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
)
_SECRET_KEYS = frozenset({
    "api_key", "password", "token", "secret", "authorization", "service_role_key",
})


def persistent_audit_enabled() -> bool:
    return os.getenv("AGENT_AUDIT_PERSIST_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def redact_text(text: str, *, max_len: int = 500) -> str:
    out = (text or "")[: max_len * 4]
    for pat in _PATIENT_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out[:max_len]


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, val in payload.items():
        lk = key.lower()
        if lk in _SECRET_KEYS:
            safe[key] = "[REDACTED]"
        elif lk in {"message", "question", "prompt", "user_content"}:
            safe[key] = redact_text(str(val), max_len=400)
        elif lk == "intermediate_outputs" and isinstance(val, list):
            safe[key] = [
                {"agent": item.get("agent"), "text": redact_text(str(item.get("text", "")), max_len=200)}
                for item in val[:6]
                if isinstance(item, dict)
            ]
        elif isinstance(val, (str, int, float, bool)) or val is None:
            safe[key] = redact_text(str(val), max_len=300) if isinstance(val, str) and len(val) > 300 else val
        elif isinstance(val, (list, dict)):
            try:
                encoded = json.dumps(val, default=str)[:800]
                safe[key] = redact_text(encoded, max_len=800)
            except Exception:
                safe[key] = "[complex]"
    return safe


def persist_agent_audit(
    trace: dict[str, Any],
    *,
    db_conn: str,
    source_buckets: list[str] | None = None,
    source_counts: dict[str, int] | None = None,
    provider: str | None = None,
    model: str | None = None,
    grounding_outcome: str | None = None,
    user_email: str | None = None,
    user_role: str | None = None,
) -> bool:
    """Write redacted audit row; return True on success, False on skip/failure."""
    if not persistent_audit_enabled():
        return False
    payload = redact_payload({
        "run_id": trace.get("run_id"),
        "category": trace.get("category"),
        "mode": trace.get("mode"),
        "agents_started": trace.get("agents_started"),
        "agents_skipped": trace.get("agents_skipped"),
        "models_used": trace.get("models_used"),
        "warnings": trace.get("warnings"),
        "latency_ms": trace.get("latency_ms"),
        "source_buckets": source_buckets or [],
        "source_counts": source_counts or {},
        "provider": provider,
        "model": model,
        "grounding_outcome": grounding_outcome,
    })
    try:
        with psycopg.connect(db_conn, connect_timeout=4) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.agent_audit_log (
                        run_id, category, mode, user_email, user_role,
                        source_buckets, source_counts, latency_ms,
                        provider, model, grounding_outcome, payload
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb);
                    """,
                    (
                        trace.get("run_id"),
                        trace.get("category"),
                        trace.get("mode"),
                        user_email,
                        user_role,
                        ",".join(source_buckets or []),
                        json.dumps(source_counts or {}),
                        trace.get("latency_ms"),
                        provider,
                        model,
                        grounding_outcome,
                        json.dumps(payload),
                    ),
                )
            conn.commit()
        return True
    except Exception as exc:
        LOGGER.debug("Persistent agent audit skipped: %s", exc)
        return False
