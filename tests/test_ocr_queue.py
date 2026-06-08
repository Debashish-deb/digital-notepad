"""OCR queue — enqueue, worker gating, pipeline continuation, retry."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from omeia.api.ocr.queue import (
    apply_ocr_result,
    enqueue_ocr_job,
    ocr_badge_for_manifest,
    requeue_ocr_for_document,
)
from omeia.digitalization.extractors import extract_file
from omeia.digitalization.models import SourceFileManifest


def test_enqueue_always_creates_job_even_when_ocr_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OCR", "false")
    cur = MagicMock()
    cur.fetchone.return_value = ("job-1",)
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    job_id = enqueue_ocr_job(
        conn,
        manifest_id="manifest-1",
        extracted_document_id="ext-1",
        source_path="/data/scan.png",
        metadata={"logical_path": "scans/scan.png"},
    )
    assert job_id == "job-1"
    assert "INSERT INTO platform.ocr_job" in cur.execute.call_args[0][0]


def test_worker_skips_when_ocr_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OCR", "false")
    from scripts.ops import run_ocr_queue

    result = run_ocr_queue.process_queue(limit=3)
    assert result["processed"] == 0
    assert result["skipped"] == "ocr_disabled"


def test_apply_ocr_result_failed_does_not_raise() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    out = apply_ocr_result(
        conn,
        job_id="job-1",
        manifest_id=None,
        extracted_document_id="ext-1",
        source_path="/tmp/missing.png",
        metadata={},
        result_text="",
        confidence=0.0,
        engine="tesseract",
        error="empty OCR result",
    )
    assert out["job_status"] == "failed"


def test_requeue_existing_failed_job(monkeypatch: pytest.MonkeyPatch) -> None:
    cur = MagicMock()
    cur.fetchone.side_effect = [
        ("m1", "e1", "scans/a.pdf", "needs_ocr", "needs_ocr"),
        ("job-old", "failed"),
    ]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    with patch("omeia.api.ocr.queue.resolve_ocr_source_path", return_value="/data/scans/a.pdf"):
        result = requeue_ocr_for_document(conn, "doc-abc")

    assert result["action"] == "requeued"
    assert result["job_id"] == "job-old"
    sql_calls = [call[0][0] for call in cur.execute.call_args_list]
    assert any("UPDATE platform.ocr_job" in sql for sql in sql_calls)


def test_ocr_badge_states() -> None:
    assert ocr_badge_for_manifest(logical_path="x", job_status="queued") == "ocr_pending"
    assert ocr_badge_for_manifest(logical_path="x", job_status="failed") == "ocr_failed"
    assert (
        ocr_badge_for_manifest(
            logical_path="x",
            job_status="completed",
            manifest_status="chunked",
            extraction_status="extracted",
        )
        == "ocr_indexed"
    )


def test_scanned_image_manifest_needs_ocr(tmp_path) -> None:
    (tmp_path / "slides").mkdir()
    img = tmp_path / "slides" / "slide.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    manifest = SourceFileManifest(
        provider="local",
        logical_path="slides/slide.png",
        file_name="slide.png",
        file_ext=".png",
        size_bytes=img.stat().st_size,
        id="manifest-png",
    )
    extracted = extract_file(manifest, tmp_path)
    assert extracted.extraction_status == "needs_ocr"


def test_process_queue_applies_backend_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OCR", "true")
    from omeia.api.ocr.adapter import OcrResult
    from scripts.ops import run_ocr_queue

    fake_backend = MagicMock()
    fake_backend.extract.return_value = OcrResult(
        text="OCR_ONLY_PHRASE_XYZ",
        confidence=0.88,
        engine="tesseract",
        metadata={},
    )

    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = [
        ("job1", "m1", "e1", "/tmp/scan.png", "tesseract", {"logical_path": "scan.png"}),
    ]
    conn.cursor.return_value.__enter__.return_value = cur
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False

    with patch("scripts.ops.run_ocr_queue._conn", return_value=conn):
        with patch("scripts.ops.run_ocr_queue.get_ocr_backend", return_value=fake_backend):
            with patch(
                "scripts.ops.run_ocr_queue.apply_ocr_result",
                return_value={"job_status": "completed", "pipeline": "completed"},
            ):
                result = run_ocr_queue.process_queue(limit=1)

    assert result["processed"] == 1
    assert result["completed"] == 1
