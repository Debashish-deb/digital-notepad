"""Regression tests for scientific-identifier allowlist and true PII blocking."""
from __future__ import annotations

import unittest

from app_skeleton.api.privacy_guardrails import allow_external_llm, audit_message, guard_for_llm


class TestScientificIdentifierAllowlist(unittest.TestCase):
    def test_gse_accession_not_blocked(self) -> None:
        audit = audit_message("Find GSE211956 in GEO")
        self.assertTrue(audit["is_safe"])
        self.assertIn("GSE211956", audit["redacted_text"])

    def test_ega_accession_not_blocked(self) -> None:
        audit = audit_message("Dataset EGAS00001004957 metadata")
        self.assertTrue(audit["is_safe"])
        self.assertIn("EGAS00001004957", audit["redacted_text"])

    def test_tcga_accession_not_blocked(self) -> None:
        audit = audit_message("Compare TCGA-OV cohorts")
        self.assertTrue(audit["is_safe"])
        self.assertIn("TCGA-OV", audit["redacted_text"])

    def test_pmid_not_blocked(self) -> None:
        audit = audit_message("See PMID: 31178118 for methods")
        self.assertTrue(audit["is_safe"])
        self.assertIn("31178118", audit["redacted_text"])

    def test_doi_not_blocked(self) -> None:
        doi = "10.1038/s41586-019-1234-x"
        audit = audit_message(f"Cite {doi} in the review")
        self.assertTrue(audit["is_safe"])
        self.assertIn(doi, audit["redacted_text"])


class TestTruePiiStillBlocked(unittest.TestCase):
    def test_patient_identifier_blocked_for_gemini(self) -> None:
        _, audit, limitations = guard_for_llm("Patient #ABC123 needs review", "gemini")
        self.assertFalse(audit["is_safe"])
        self.assertFalse(allow_external_llm(audit, "gemini"))
        self.assertTrue(any("blocked" in note.lower() for note in limitations))

    def test_hetu_blocked_for_gemini(self) -> None:
        _, audit, _ = guard_for_llm("Subject 010180-123A birth cohort", "gemini")
        self.assertFalse(audit["is_safe"])
        self.assertFalse(allow_external_llm(audit, "gemini"))

    def test_mrn_blocked_for_gemini(self) -> None:
        _, audit, _ = guard_for_llm("Pull chart for MRN: XY-998812", "gemini")
        self.assertFalse(audit["is_safe"])
        self.assertFalse(allow_external_llm(audit, "gemini"))

    def test_openai_style_api_key_blocked(self) -> None:
        _, audit, _ = guard_for_llm("My key is sk-abcdefghijklmnopqrstuvwxyz123456", "gemini")
        self.assertFalse(audit["is_safe"])
        self.assertFalse(allow_external_llm(audit, "gemini"))

    def test_google_api_key_blocked(self) -> None:
        _, audit, _ = guard_for_llm("Use AIzaSyDUMMYKEYFORUNITTEST000000000", "gemini")
        self.assertFalse(audit["is_safe"])
        self.assertFalse(allow_external_llm(audit, "gemini"))


if __name__ == "__main__":
    unittest.main()
