"""OCR adapter interface — pluggable backends for scanned document text extraction."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


def ocr_enabled() -> bool:
    from omeia.api.platform_flags import ocr_enabled as _flag

    return _flag()


@dataclass
class OcrResult:
    text: str
    confidence: float
    engine: str
    metadata: dict[str, Any]


class OcrBackend(ABC):
    @abstractmethod
    def extract(self, source_path: str, *, metadata: dict[str, Any] | None = None) -> OcrResult:
        ...


def get_ocr_backend() -> OcrBackend | None:
    if not ocr_enabled():
        return None
    engine = (os.getenv("OCR_ENGINE", "tesseract") or "tesseract").strip().lower()
    if engine == "tesseract":
        from omeia.api.ocr.tesseract_backend import TesseractBackend

        return TesseractBackend()
    return None
