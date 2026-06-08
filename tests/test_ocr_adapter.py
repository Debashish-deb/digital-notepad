"""Phase 3 — OCR adapter flag gating (no tesseract required)."""
from __future__ import annotations

import pytest

from app_skeleton.api.ocr.adapter import get_ocr_backend, ocr_enabled
from app_skeleton.api.ocr.tesseract_backend import TesseractBackend


def test_ocr_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENABLE_OCR", raising=False)
    assert ocr_enabled() is False
    assert get_ocr_backend() is None


def test_ocr_backend_none_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OCR", "false")
    assert get_ocr_backend() is None


def test_tesseract_backend_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OCR", "false")
    result = TesseractBackend().extract("/tmp/sample.png")
    assert result.text == ""
    assert result.metadata.get("skipped") == "ENABLE_OCR=false"
