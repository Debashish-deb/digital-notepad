"""Tesseract OCR backend (stub when ENABLE_OCR=false)."""
from __future__ import annotations

import shutil
from typing import Any

from app_skeleton.api.ocr.adapter import OcrBackend, OcrResult, ocr_enabled


class TesseractBackend(OcrBackend):
    def extract(self, source_path: str, *, metadata: dict[str, Any] | None = None) -> OcrResult:
        if not ocr_enabled():
            return OcrResult(text="", confidence=0.0, engine="tesseract", metadata={"skipped": "ENABLE_OCR=false"})
        if not shutil.which("tesseract"):
            return OcrResult(
                text="",
                confidence=0.0,
                engine="tesseract",
                metadata={"error": "tesseract binary not found"},
            )
        # Full page OCR wiring deferred to Phase 3 worker; return stub for queue integration.
        return OcrResult(
            text="",
            confidence=0.0,
            engine="tesseract",
            metadata={"source_path": source_path, "status": "not_implemented"},
        )
