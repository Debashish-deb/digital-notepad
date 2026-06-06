"""Privacy guardrails for Gemini / external LLM chat endpoints.

Runs before any query is forwarded to a cloud provider. Reuses the conservative
redaction patterns from PrivacyGuardrailAgent while exposing a small API for
chat_service and routers.
"""
from __future__ import annotations

import os
from typing import Any

from app_skeleton.api.agents import PrivacyGuardrailAgent

EXTERNAL_CLOUD_PROVIDERS = frozenset({
    "openai",
    "groq",
    "openrouter",
    "together",
    "deepseek",
    "gemini",
})

LOCAL_SAFE_PROVIDERS = frozenset({"mock", "ollama"})


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def is_external_provider(provider: str) -> bool:
    return (provider or "mock").strip().lower() in EXTERNAL_CLOUD_PROVIDERS


def audit_message(text: str) -> dict[str, Any]:
    """Audit user text for patient identifiers and other sensitive patterns."""
    return PrivacyGuardrailAgent.audit_query(text)


def allow_external_llm(audit: dict[str, Any], provider: str) -> bool:
    """Return True when the provider may receive the (possibly redacted) text."""
    if not is_external_provider(provider):
        return True
    if _env_bool("ALLOW_PATIENT_DATA", False):
        return True
    return bool(audit.get("is_safe"))


def guard_for_llm(text: str, provider: str) -> tuple[str, dict[str, Any], list[str]]:
    """Redact text and decide whether an external LLM call is permitted.

    Returns:
        safe_text: redacted query text safe to embed/retrieve with
        audit: full audit payload
        limitations: human-readable guardrail notes for the API response
    """
    audit = audit_message(text)
    limitations: list[str] = []

    if audit.get("redaction_count", 0) > 0:
        limitations.append(
            "Privacy guardrail: potential identifiers were redacted before retrieval/LLM."
        )

    if not allow_external_llm(audit, provider):
        violations = ", ".join(audit.get("violations") or [])
        limitations.append(
            f"Safety alert: query blocked for external LLM because patient-identifiable data was detected ({violations})."
        )

    return str(audit.get("redacted_text") or text), audit, limitations
