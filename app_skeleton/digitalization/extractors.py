"""Extractors — wraps existing document_extraction.py to produce ExtractedDocument records."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app_skeleton.digitalization.models import ExtractedDocument, SourceFileManifest
from app_skeleton.digitalization.status import Status

LOGGER = logging.getLogger(__name__)

IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".bmp", ".svg"})


def _get_de():
    """Lazy import of document_extraction to avoid circular imports."""
    from app_skeleton.api import document_extraction as de
    return de


def extract_file(manifest: SourceFileManifest, root: Path) -> ExtractedDocument:
    """Extract actual content from a file. Returns ExtractedDocument with real text, not just a path."""
    de = _get_de()
    abs_path = (root / manifest.logical_path).resolve()

    if not abs_path.is_file():
        return ExtractedDocument(
            manifest_id=manifest.id or "",
            extraction_status="extraction_failed",
            extractor_name="file_missing",
            warnings=[f"File not found: {manifest.logical_path}"],
        )

    ext = manifest.file_ext.lower()

    # Images: metadata only unless OCR is available
    if ext in IMAGE_EXTENSIONS:
        return _extract_image_metadata(manifest, abs_path, de)

    try:
        result = de._extract_file(abs_path, root)
    except Exception as exc:
        LOGGER.warning("Extraction failed for %s: %s", manifest.logical_path, exc)
        return ExtractedDocument(
            manifest_id=manifest.id or "",
            extraction_status="extraction_failed",
            extractor_name="document_extraction",
            warnings=[f"Exception: {str(exc)[:500]}"],
        )

    # Map ExtractionResult -> ExtractedDocument
    raw_text = result.text or ""
    extraction_status = _map_extraction_status(result.status, raw_text, ext)
    confidence = _estimate_confidence(raw_text, result.status, ext)

    raw_tables: list[dict[str, Any]] = []
    if result.metadata.get("sheets"):
        raw_tables = result.metadata["sheets"]
    elif result.metadata.get("tables"):
        raw_tables = result.metadata["tables"]

    raw_metadata: dict[str, Any] = {
        "extractor": result.extractor,
        "document_kind": result.document_kind,
        "char_count": result.char_count,
        "word_count": result.word_count,
        "title": result.title,
        "excerpt": result.excerpt[:500] if result.excerpt else "",
    }
    # Copy safe metadata
    for key in ("page_count", "sheet_count", "slide_count", "line_count", "image_dimensions"):
        if key in result.metadata:
            raw_metadata[key] = result.metadata[key]

    return ExtractedDocument(
        manifest_id=manifest.id or "",
        raw_text=raw_text,
        raw_tables=raw_tables,
        raw_metadata=raw_metadata,
        extractor_name=result.extractor or "document_extraction",
        extraction_status=extraction_status,
        extraction_confidence=confidence,
        warnings=result.warnings[:20] + result.errors[:10],
    )


def _extract_image_metadata(manifest: SourceFileManifest, abs_path: Path, de) -> ExtractedDocument:
    """For images, extract metadata only. Mark as needs_ocr."""
    metadata: dict[str, Any] = {"document_kind": "image"}
    try:
        from PIL import Image
        with Image.open(abs_path) as im:
            metadata["image_dimensions"] = {"width": im.width, "height": im.height}
            metadata["image_mode"] = im.mode
    except Exception:
        pass

    return ExtractedDocument(
        manifest_id=manifest.id or "",
        raw_text="",
        raw_metadata=metadata,
        extractor_name="image_metadata",
        extraction_status="needs_ocr",
        extraction_confidence=0.0,
        warnings=["Image file — no text extraction. Requires OCR for content."],
    )


def _map_extraction_status(result_status: str, raw_text: str, ext: str) -> str:
    """Map ExtractionResult.status to our pipeline status."""
    if result_status == "failed":
        return "extraction_failed"
    if result_status in ("skipped", "metadata_only"):
        if ext in IMAGE_EXTENSIONS:
            return "needs_ocr"
        return "metadata_only"
    if not raw_text or len(raw_text.strip()) < 5:
        if ext in IMAGE_EXTENSIONS or ext == ".pdf":
            return "needs_ocr"
        return "extraction_failed"
    if ext == ".pdf" and len(raw_text.strip()) < 40 and result_status in ("empty", "metadata_only"):
        return "needs_ocr"
    return "extracted"


def _estimate_confidence(raw_text: str, result_status: str, ext: str) -> float:
    """Rough extraction confidence based on text quality."""
    if not raw_text or result_status == "failed":
        return 0.0
    text_len = len(raw_text.strip())
    if text_len < 20:
        return 0.1
    if text_len < 100:
        return 0.3
    if text_len < 500:
        return 0.5
    # Higher confidence for text-native formats
    if ext in (".txt", ".md", ".csv", ".json", ".yaml", ".yml"):
        return 0.95
    if ext in (".docx", ".xlsx", ".pptx"):
        return 0.85
    if ext == ".pdf":
        return 0.75
    return 0.7
