"""Tesseract OCR backend — subprocess-based with graceful degradation."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from omeia.api.ocr.adapter import OcrBackend, OcrResult, ocr_enabled

LOGGER = logging.getLogger(__name__)

IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".bmp"})
PDF_EXTENSIONS = frozenset({".pdf"})


def _parse_tsv_confidence(tsv_text: str) -> float:
    """Average word confidence from Tesseract TSV output (0–1 scale)."""
    scores: list[float] = []
    for line in tsv_text.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 12:
            continue
        conf_raw = parts[10].strip()
        word = parts[11].strip() if len(parts) > 11 else ""
        if not word or conf_raw in ("", "-1"):
            continue
        try:
            conf = float(conf_raw)
        except ValueError:
            continue
        if conf >= 0:
            scores.append(conf / 100.0)
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _run_tesseract(image_path: Path, *, lang: str = "eng", timeout: int = 120) -> tuple[str, float]:
    text_proc = subprocess.run(
        ["tesseract", str(image_path), "stdout", "-l", lang],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    text = (text_proc.stdout or "").strip()
    if text_proc.returncode != 0:
        err = (text_proc.stderr or "").strip()
        if err:
            LOGGER.debug("tesseract text pass stderr: %s", err[:300])
        return "", 0.0

    tsv_proc = subprocess.run(
        ["tesseract", str(image_path), "stdout", "-l", lang, "tsv"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    confidence = _parse_tsv_confidence(tsv_proc.stdout or "") if tsv_proc.returncode == 0 else 0.0
    if confidence == 0.0 and text:
        confidence = 0.5
    return text, confidence


def _pdf_to_images(pdf_path: Path, tmp_dir: Path) -> list[Path]:
    if not shutil.which("pdftoppm"):
        return []
    prefix = tmp_dir / "page"
    proc = subprocess.run(
        ["pdftoppm", "-png", str(pdf_path), str(prefix)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if proc.returncode != 0:
        LOGGER.warning("pdftoppm failed for %s: %s", pdf_path, (proc.stderr or "")[:300])
        return []
    return sorted(tmp_dir.glob("page-*.png"))


def _prepare_image_path(source_path: Path, tmp_dir: Path) -> Path | None:
    ext = source_path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        if ext in (".tif", ".tiff"):
            try:
                from PIL import Image

                with Image.open(source_path) as im:
                    out = tmp_dir / "frame.png"
                    im.convert("RGB").save(out, format="PNG")
                    return out
            except Exception as exc:
                LOGGER.warning("TIFF open failed for %s: %s", source_path, exc)
                return None
        return source_path
    return None


class TesseractBackend(OcrBackend):
    def extract(self, source_path: str, *, metadata: dict[str, Any] | None = None) -> OcrResult:
        meta = dict(metadata or {})
        if not ocr_enabled():
            return OcrResult(
                text="",
                confidence=0.0,
                engine="tesseract",
                metadata={**meta, "skipped": "ENABLE_OCR=false"},
            )
        if not shutil.which("tesseract"):
            return OcrResult(
                text="",
                confidence=0.0,
                engine="tesseract",
                metadata={**meta, "error": "tesseract binary not found"},
            )

        path = Path(source_path)
        if not path.is_file():
            return OcrResult(
                text="",
                confidence=0.0,
                engine="tesseract",
                metadata={**meta, "error": f"source not found: {source_path}"},
            )

        ext = path.suffix.lower()
        lang = str(meta.get("lang") or "eng")

        try:
            with tempfile.TemporaryDirectory(prefix="omeia_ocr_") as tmp:
                tmp_dir = Path(tmp)
                page_texts: list[str] = []
                page_scores: list[float] = []

                if ext in PDF_EXTENSIONS:
                    images = _pdf_to_images(path, tmp_dir)
                    if not images:
                        return OcrResult(
                            text="",
                            confidence=0.0,
                            engine="tesseract",
                            metadata={
                                **meta,
                                "error": "pdftoppm unavailable or produced no pages",
                                "source_path": source_path,
                            },
                        )
                    for image in images:
                        text, conf = _run_tesseract(image, lang=lang)
                        if text:
                            page_texts.append(text)
                            page_scores.append(conf)
                else:
                    image_path = _prepare_image_path(path, tmp_dir)
                    if image_path is None:
                        return OcrResult(
                            text="",
                            confidence=0.0,
                            engine="tesseract",
                            metadata={**meta, "error": f"unsupported extension: {ext}", "source_path": source_path},
                        )
                    text, conf = _run_tesseract(image_path, lang=lang)
                    if text:
                        page_texts.append(text)
                        page_scores.append(conf)

                merged = "\n\n".join(page_texts).strip()
                confidence = (sum(page_scores) / len(page_scores)) if page_scores else 0.0
                return OcrResult(
                    text=merged,
                    confidence=confidence,
                    engine="tesseract",
                    metadata={
                        **meta,
                        "source_path": source_path,
                        "page_count": len(page_texts),
                        "lang": lang,
                    },
                )
        except subprocess.TimeoutExpired:
            return OcrResult(
                text="",
                confidence=0.0,
                engine="tesseract",
                metadata={**meta, "error": "tesseract timeout", "source_path": source_path},
            )
        except Exception as exc:
            LOGGER.warning("Tesseract OCR failed for %s: %s", source_path, exc)
            return OcrResult(
                text="",
                confidence=0.0,
                engine="tesseract",
                metadata={**meta, "error": str(exc)[:500], "source_path": source_path},
            )
