-- 145_ocr_jobs.sql — OCR job queue for scanned / low-text documents (Phase 3)
CREATE SCHEMA IF NOT EXISTS platform;

CREATE TABLE IF NOT EXISTS platform.ocr_job (
    job_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manifest_id           UUID REFERENCES platform.source_file_manifest(id) ON DELETE SET NULL,
    extracted_document_id UUID REFERENCES platform.extracted_document(id) ON DELETE SET NULL,
    document_id           UUID,
    asset_id              TEXT,
    source_path           TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'queued',
    engine                TEXT NOT NULL DEFAULT 'tesseract',
    attempt_count         INTEGER NOT NULL DEFAULT 0,
    max_attempts          INTEGER NOT NULL DEFAULT 3,
    error_message         TEXT,
    confidence_score      REAL,
    result_text           TEXT,
    metadata              JSONB NOT NULL DEFAULT '{}'::jsonb,
    queued_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at            TIMESTAMPTZ,
    finished_at           TIMESTAMPTZ,
    CONSTRAINT ocr_job_status_chk CHECK (
        status IN ('queued', 'processing', 'completed', 'failed', 'review')
    )
);

CREATE INDEX IF NOT EXISTS idx_ocr_job_status
    ON platform.ocr_job (status)
    WHERE status IN ('queued', 'processing');

CREATE INDEX IF NOT EXISTS idx_ocr_job_manifest
    ON platform.ocr_job (manifest_id)
    WHERE manifest_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ocr_job_asset
    ON platform.ocr_job (asset_id)
    WHERE asset_id IS NOT NULL;
