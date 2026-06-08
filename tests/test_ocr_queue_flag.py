"""OCR queue worker and enqueue behavior behind ENABLE_OCR."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from omeia.api.ocr.queue import enqueue_ocr_job
from omeia.api.platform_flags import ocr_enabled


def test_platform_flags_ocr_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENABLE_OCR", raising=False)
    assert ocr_enabled() is False


def test_enqueue_inserts_even_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OCR", "false")
    cur = MagicMock()
    cur.fetchone.return_value = ("job-uuid-2",)
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    job_id = enqueue_ocr_job(
        conn,
        manifest_id="m1",
        extracted_document_id="d1",
        source_path="/tmp/scan.png",
    )
    assert job_id == "job-uuid-2"


def test_enqueue_inserts_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setenv("OCR_ENGINE", "tesseract")

    cur = MagicMock()
    cur.fetchone.return_value = ("job-uuid-1",)
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    job_id = enqueue_ocr_job(
        conn,
        manifest_id="m1",
        extracted_document_id="d1",
        source_path="/tmp/scan.png",
        root_path="/data/root",
        metadata={"logical_path": "docs/scan.png"},
    )
    assert job_id == "job-uuid-1"
    sql = cur.execute.call_args[0][0]
    assert "INSERT INTO platform.ocr_job" in sql
    assert cur.execute.call_args[0][1][5] == "tesseract"


def test_process_queue_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OCR", "false")
    from scripts.ops import run_ocr_queue

    result = run_ocr_queue.process_queue(limit=5)
    assert result["processed"] == 0
    assert result["skipped"] == "ocr_disabled"


def test_process_queue_uses_backend_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setenv("OCR_ENGINE", "tesseract")

    from omeia.api.ocr.adapter import OcrResult
    from scripts.ops import run_ocr_queue

    fake_backend = MagicMock()
    fake_backend.extract.return_value = OcrResult(
        text="recognized",
        confidence=0.9,
        engine="tesseract",
        metadata={},
    )

    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = [
        ("job1", "manifest1", "doc1", "/tmp/scan.png", "tesseract", {"root_path": "/data"}),
    ]
    conn.cursor.return_value.__enter__.return_value = cur
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False

    with patch("scripts.ops.run_ocr_queue._conn", return_value=conn):
        with patch("scripts.ops.run_ocr_queue.get_ocr_backend", return_value=fake_backend):
            with patch("scripts.ops.run_ocr_queue.apply_ocr_result", return_value={"job_status": "completed"}) as apply_mock:
                result = run_ocr_queue.process_queue(limit=1)

    assert result["processed"] == 1
    assert result["completed"] == 1
    fake_backend.extract.assert_called_once_with("/tmp/scan.png", metadata={"root_path": "/data"})
    apply_mock.assert_called_once()
