"""Tests for persistent agent audit redaction and in-memory fallback."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from omeia.api.agent_orchestrator.persistent_audit import (
    persist_agent_audit,
    redact_payload,
    redact_text,
)
from omeia.api.agent_orchestrator.trace_store import create_trace, finalize_trace, get_trace


class TestAuditLogging(unittest.TestCase):
    def test_redact_patient_identifiers(self) -> None:
        text = "Patient MRN: 12345678 and SSN 123-45-6789 noted."
        redacted = redact_text(text)
        self.assertNotIn("12345678", redacted)
        self.assertNotIn("123-45-6789", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_redact_secrets_in_payload(self) -> None:
        payload = redact_payload({
            "api_key": "sk-secret",
            "message": "Long " * 200,
            "category": "general_research",
        })
        self.assertEqual(payload["api_key"], "[REDACTED]")
        self.assertLessEqual(len(str(payload["message"])), 400)

    def test_persist_skipped_when_disabled(self) -> None:
        os.environ["AGENT_AUDIT_PERSIST_ENABLED"] = "false"
        trace = create_trace(category="general_research", mode="fast")
        ok = persist_agent_audit(trace, db_conn="postgresql://invalid:5432/nodb")
        self.assertFalse(ok)

    def test_in_memory_trace_fallback(self) -> None:
        trace = create_trace(category="protocols", mode="balanced")
        trace["agents_started"].append("rag_specialist")
        finalize_trace(trace, db_conn="postgresql://invalid:5432/nodb")
        stored = get_trace(trace["run_id"])
        self.assertIsNotNone(stored)
        self.assertGreaterEqual(stored.get("latency_ms", 0), 0)
        self.assertIn("latency_ms", stored)

    def test_persist_attempts_db_when_enabled(self) -> None:
        os.environ["AGENT_AUDIT_PERSIST_ENABLED"] = "true"
        trace = create_trace(category="general_research", mode="fast")
        with patch("omeia.api.agent_orchestrator.persistent_audit.psycopg.connect") as mock_conn:
            mock_conn.side_effect = Exception("db unavailable")
            ok = persist_agent_audit(
                trace,
                db_conn="postgresql://invalid:5432/nodb",
                source_buckets=["lab"],
                source_counts={"lab": 2},
            )
        self.assertFalse(ok)
        self.assertIsNotNone(get_trace(trace["run_id"]))


if __name__ == "__main__":
    unittest.main()
