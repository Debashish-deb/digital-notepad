"""Detect secrets (passwords, API keys, tokens) and redact them from text."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

# ── Patterns ──────────────────────────────────────────────────
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("api_key", re.compile(
        r"(?:api[_\-]?key|apikey|api[_\-]?secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{16,})['\"]?",
        re.I,
    )),
    ("bearer_token", re.compile(
        r"(?:bearer|authorization)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{20,})['\"]?",
        re.I,
    )),
    ("password", re.compile(
        r"(?:password|passwd|salasana|lösenord)\s*[:=]\s*['\"]?(.{4,60})['\"]?",
        re.I,
    )),
    ("private_key", re.compile(
        r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----",
        re.I,
    )),
    ("aws_key", re.compile(
        r"(?:AKIA|ASIA)[A-Z0-9]{12,}",
    )),
    ("generic_secret", re.compile(
        r"(?:secret|token|credential)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{12,})['\"]?",
        re.I,
    )),
    ("security_question", re.compile(
        r"(?:security\s+question|secret\s+question)\s*[:=]\s*(.+)",
        re.I,
    )),
]


@dataclass
class SecretMatch:
    secret_type: str
    start: int
    end: int
    matched_text: str
    vault_ref: str = ""


@dataclass
class SecretScanResult:
    has_secrets: bool = False
    matches: list[SecretMatch] = field(default_factory=list)
    redacted_text: str = ""
    vault_references: list[dict[str, Any]] = field(default_factory=list)


def scan_for_secrets(text: str) -> SecretScanResult:
    """Scan text for secrets. Returns redacted text with vault placeholders."""
    if not text:
        return SecretScanResult(redacted_text=text)

    matches: list[SecretMatch] = []
    for secret_type, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            vault_ref = f"vault_ref_{uuid.uuid4().hex[:12]}"
            matches.append(SecretMatch(
                secret_type=secret_type,
                start=m.start(),
                end=m.end(),
                matched_text=m.group(0),
                vault_ref=vault_ref,
            ))

    if not matches:
        return SecretScanResult(redacted_text=text)

    # Sort by position descending so we can replace without shifting offsets
    matches.sort(key=lambda m: m.start, reverse=True)

    # De-duplicate overlapping matches (keep the longer/earlier one)
    deduped: list[SecretMatch] = []
    for m in matches:
        if not deduped or m.end <= deduped[-1].start:
            deduped.append(m)
    deduped.reverse()

    redacted = text
    vault_refs: list[dict[str, Any]] = []
    for m in reversed(deduped):
        placeholder = f"[REDACTED: {m.vault_ref}]"
        redacted = redacted[:m.start] + placeholder + redacted[m.end:]
        vault_refs.append({
            "vault_ref": m.vault_ref,
            "secret_type": m.secret_type,
            "original_length": len(m.matched_text),
        })

    return SecretScanResult(
        has_secrets=True,
        matches=deduped,
        redacted_text=redacted,
        vault_references=vault_refs,
    )
