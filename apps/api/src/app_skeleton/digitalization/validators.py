"""Validators — validate canonical JSON schema and detect quality issues."""
from __future__ import annotations

from typing import Any

from app_skeleton.digitalization.models import CanonicalDocument
from app_skeleton.digitalization.secret_detector import scan_for_secrets


def validate_canonical(doc: CanonicalDocument) -> tuple[str, list[str]]:
    """Validate a canonical document. Returns (status, warnings)."""
    warnings: list[str] = list(doc.warnings or [])

    # 1. Check canonical_json is populated
    cj = doc.canonical_json
    if not cj or not isinstance(cj, dict):
        warnings.append("canonical_json is empty or invalid")
        return "validation_failed", warnings

    # 2. Schema version
    if cj.get("schema_version") != "1.0":
        warnings.append(f"Unexpected schema_version: {cj.get('schema_version')}")

    # 3. Document ID
    if not doc.document_id or len(doc.document_id) < 5:
        warnings.append("Missing or invalid document_id")
        return "validation_failed", warnings

    # 4. Source block
    source = cj.get("source", {})
    if not source.get("file_name"):
        warnings.append("Missing source.file_name")
    if not source.get("logical_path"):
        warnings.append("Missing source.logical_path")

    # 5. Title
    if not doc.title or len(doc.title.strip()) < 2:
        warnings.append("Missing or too-short title")

    # 6. Empty/path-only detection
    text = doc.canonical_text or ""
    if len(text.strip()) < 20:
        warnings.append("canonical_text too short (<20 chars) — likely empty extraction")
        return "validation_failed", warnings

    # 7. Path-only fake detection
    if _is_path_only(text):
        warnings.append("canonical_text appears to be path-only — not real extracted content")
        return "validation_failed", warnings

    # 8. Classification
    if doc.document_type == "unknown" and doc.domain == "unknown":
        warnings.append("Both document_type and domain are unknown — needs review")

    # 9. Secret detection in canonical_text
    secret_scan = scan_for_secrets(text)
    if secret_scan.has_secrets:
        warnings.append(f"Secrets detected in canonical_text: {len(secret_scan.matches)} match(es)")

    # 10. Determine final status
    has_critical = any("validation_failed" in w.lower() or "empty extraction" in w.lower() for w in warnings)
    if has_critical:
        return "validation_failed", warnings

    return "validated", warnings


def _is_path_only(text: str) -> bool:
    """Detect if text is just a file path pretending to be content."""
    stripped = text.strip()
    if not stripped:
        return True
    lines = [l.strip() for l in stripped.split("\n") if l.strip()]
    if len(lines) == 0:
        return True
    if len(lines) <= 2:
        # Check if every line looks like a path
        for line in lines:
            if line.startswith("/") or line.startswith("\\") or ":\\" in line:
                continue
            if "/" in line and len(line.split()) == 1:
                continue
            return False
        return True
    return False
