-- OCR job queue for scanned / low-text documents (Phase 3)
CREATE SCHEMA IF NOT EXISTS platform;

CREATE TABLE IF NOT EXISTS platform.ocr_job (
    job_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id       UUID,
    asset_id          TEXT,
    source_path       TEXT,
    status            TEXT NOT NULL DEFAULT 'queued',
    engine            TEXT NOT NULL DEFAULT 'tesseract',
    attempt_count     INTEGER NOT NULL DEFAULT 0,
    max_attempts      INTEGER NOT NULL DEFAULT 3,
    error_message     TEXT,
    confidence_score  REAL,
    result_text       TEXT,
    metadata          JSONB NOT NULL DEFAULT '{}'::jsonb,
    queued_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at        TIMESTAMPTZ,
    finished_at       TIMESTAMPTZ,
    CONSTRAINT ocr_job_status_chk CHECK (status IN ('queued', 'running', 'success', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_ocr_job_status ON platform.ocr_job (status) WHERE status IN ('queued', 'running');
CREATE INDEX IF NOT EXISTS idx_ocr_job_asset ON platform.ocr_job (asset_id) WHERE asset_id IS NOT NULL;
