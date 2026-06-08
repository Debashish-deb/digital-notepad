"""Privacy guardrails for Gemini / external LLM chat endpoints.

Runs before any query is forwarded to a cloud provider. Reuses the conservative
redaction patterns from PrivacyGuardrailAgent while exposing a small API for
chat_service and routers.

Scientific identifiers (GEO/EGA/TCGA accessions, DOIs, PMIDs, etc.) are masked
before PII regexes so they are never false-positive blocked.
"""
from __future__ import annotations

import os
import re
from typing import Any

from omeia.api.agents import PrivacyGuardrailAgent

EXTERNAL_CLOUD_PROVIDERS = frozenset({
    "openai",
    "groq",
    "openrouter",
    "together",
    "deepseek",
    "gemini",
})

LOCAL_SAFE_PROVIDERS = frozenset({"mock", "ollama"})

# Scientific / research identifiers — must never be treated as patient PII.
SCIENTIFIC_ALLOWLIST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bGSE\d+\b", re.I),
    re.compile(r"\bGSM\d+\b", re.I),
    re.compile(r"\bGPL\d+\b", re.I),
    re.compile(r"\bPRJNA\d+\b", re.I),
    re.compile(r"\bSRR\d+\b", re.I),
    re.compile(r"\bSRX\d+\b", re.I),
    re.compile(r"\bEGAS\d+\b", re.I),
    re.compile(r"\bEGAD\d+\b", re.I),
    re.compile(r"\bphs\d+(?:\.v\d+)?\b", re.I),
    re.compile(r"\bTCGA-[A-Z0-9-]+\b", re.I),
    re.compile(r"\b10\.\d{4,}/[^\s]+", re.I),
    re.compile(r"\bPMID:?\s*\d+\b", re.I),
    re.compile(r"\bKi-?\d+\b", re.I),  # Ki-67 and similar antibody markers
    re.compile(r"\bCD\d{1,2}[A-Za-z-]*\b"),  # CD3, CD8, CD3-OKT3 clone formats
]

# Credential patterns that must always block external LLM forwarding.
SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "API secret key"),
    (re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"), "Google API key"),
    (re.compile(r"\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[^'\"\s]{8,}", re.I), "Embedded credential"),
]


def _mask_allowlisted_spans(text: str) -> tuple[str, dict[str, str]]:
    """Replace allowlisted scientific spans with placeholders before PII scan."""
    masked = str(text or "")
    placeholders: dict[str, str] = {}
    counter = 0

    for pattern in SCIENTIFIC_ALLOWLIST_PATTERNS:
        for match in pattern.finditer(masked):
            original = match.group(0)
            key = f"__SCI_ALLOW_{counter}__"
            counter += 1
            placeholders[key] = original
            masked = masked.replace(original, key, 1)

    return masked, placeholders


def _unmask_allowlisted_spans(text: str, placeholders: dict[str, str]) -> str:
    restored = str(text or "")
    for key, original in placeholders.items():
        restored = restored.replace(key, original)
    return restored


def _audit_secrets(text: str) -> dict[str, Any]:
    violations: list[str] = []
    redacted = str(text or "")
    redaction_count = 0

    for pattern, label in SECRET_PATTERNS:
        matches = list(pattern.finditer(redacted))
        if not matches:
            continue
        violations.append(label)
        redaction_count += len(matches)
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)

    return {
        "violations": violations,
        "redacted_text": redacted,
        "redaction_count": redaction_count,
        "is_safe": len(violations) == 0,
    }


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def is_external_provider(provider: str) -> bool:
    return (provider or "mock").strip().lower() in EXTERNAL_CLOUD_PROVIDERS


def audit_message(text: str) -> dict[str, Any]:
    """Audit user text for patient identifiers and other sensitive patterns."""
    secret_audit = _audit_secrets(text)
    if not secret_audit["is_safe"]:
        return {
            "is_safe": False,
            "violations": secret_audit["violations"],
            "redacted_text": secret_audit["redacted_text"],
            "redaction_count": secret_audit["redaction_count"],
            "risk_level": "blocked_for_external_llm",
        }

    masked, placeholders = _mask_allowlisted_spans(text)
    audit = PrivacyGuardrailAgent.audit_query(masked)
    audit["redacted_text"] = _unmask_allowlisted_spans(audit.get("redacted_text") or masked, placeholders)
    return audit


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
