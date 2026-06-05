-- 140_document_digitalization_pipeline.sql
-- Professional data digitalization pipeline tables.
-- Separates discovery, extraction, canonicalization, and chunking.

CREATE SCHEMA IF NOT EXISTS platform;

-- ============================================================
-- 1. Source File Manifest — discovered files before extraction
-- ============================================================
CREATE TABLE IF NOT EXISTS platform.source_file_manifest (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider        text NOT NULL,
    logical_path    text NOT NULL,
    source_uri      text,
    file_name       text NOT NULL,
    file_ext        text NOT NULL DEFAULT '',
    size_bytes      bigint NOT NULL DEFAULT 0,
    modified_at     timestamptz,
    checksum_sha256 text,
    discovered_at   timestamptz NOT NULL DEFAULT now(),
    status          text NOT NULL DEFAULT 'discovered',
    metadata        jsonb NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, logical_path, checksum_sha256)
);

CREATE INDEX IF NOT EXISTS idx_sfm_provider_path
    ON platform.source_file_manifest (provider, logical_path);
CREATE INDEX IF NOT EXISTS idx_sfm_status
    ON platform.source_file_manifest (status);
CREATE INDEX IF NOT EXISTS idx_sfm_checksum
    ON platform.source_file_manifest (checksum_sha256);
CREATE INDEX IF NOT EXISTS idx_sfm_discovered
    ON platform.source_file_manifest (discovered_at);

-- ============================================================
-- 2. Digitalization Job — tracks pipeline runs
-- ============================================================
CREATE TABLE IF NOT EXISTS platform.digitalization_job (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider        text NOT NULL DEFAULT 'local',
    root_path       text NOT NULL DEFAULT '',
    status          text NOT NULL DEFAULT 'pending',
    started_at      timestamptz,
    finished_at     timestamptz,
    total_files     int NOT NULL DEFAULT 0,
    processed_files int NOT NULL DEFAULT 0,
    failed_files    int NOT NULL DEFAULT 0,
    dry_run         boolean NOT NULL DEFAULT false,
    error_summary   jsonb NOT NULL DEFAULT '{}',
    created_by      text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dj_status
    ON platform.digitalization_job (status);
CREATE INDEX IF NOT EXISTS idx_dj_created
    ON platform.digitalization_job (created_at);

-- ============================================================
-- 3. Extracted Document — raw extracted content per file
-- ============================================================
CREATE TABLE IF NOT EXISTS platform.extracted_document (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    manifest_id             uuid NOT NULL REFERENCES platform.source_file_manifest(id) ON DELETE CASCADE,
    raw_text                text NOT NULL DEFAULT '',
    raw_tables              jsonb NOT NULL DEFAULT '[]',
    raw_metadata            jsonb NOT NULL DEFAULT '{}',
    extractor_name          text NOT NULL DEFAULT 'unknown',
    extraction_status       text NOT NULL DEFAULT 'not_attempted',
    extraction_confidence   numeric(5,4) NOT NULL DEFAULT 0.0,
    warnings                jsonb NOT NULL DEFAULT '[]',
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ed_manifest
    ON platform.extracted_document (manifest_id);
CREATE INDEX IF NOT EXISTS idx_ed_status
    ON platform.extracted_document (extraction_status);

-- ============================================================
-- 4. Canonical Document — normalized, validated, structured
-- ============================================================
CREATE TABLE IF NOT EXISTS platform.canonical_document (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    manifest_id             uuid NOT NULL REFERENCES platform.source_file_manifest(id) ON DELETE CASCADE,
    extracted_document_id   uuid NOT NULL REFERENCES platform.extracted_document(id) ON DELETE CASCADE,
    document_id             text NOT NULL UNIQUE,
    title                   text NOT NULL DEFAULT '',
    document_type           text NOT NULL DEFAULT 'unknown',
    domain                  text NOT NULL DEFAULT 'unknown',
    language_original       text NOT NULL DEFAULT 'unknown',
    language_canonical      text NOT NULL DEFAULT 'en',
    canonical_json          jsonb NOT NULL DEFAULT '{}',
    canonical_text          text NOT NULL DEFAULT '',
    short_summary           text NOT NULL DEFAULT '',
    should_index            boolean NOT NULL DEFAULT true,
    needs_review            boolean NOT NULL DEFAULT false,
    validation_status       text NOT NULL DEFAULT 'not_validated',
    warnings                jsonb NOT NULL DEFAULT '[]',
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cd_manifest
    ON platform.canonical_document (manifest_id);
CREATE INDEX IF NOT EXISTS idx_cd_doctype
    ON platform.canonical_document (document_type);
CREATE INDEX IF NOT EXISTS idx_cd_domain
    ON platform.canonical_document (domain);
CREATE INDEX IF NOT EXISTS idx_cd_should_index
    ON platform.canonical_document (should_index);
CREATE INDEX IF NOT EXISTS idx_cd_needs_review
    ON platform.canonical_document (needs_review);
CREATE INDEX IF NOT EXISTS idx_cd_validation
    ON platform.canonical_document (validation_status);
CREATE INDEX IF NOT EXISTS idx_cd_created
    ON platform.canonical_document (created_at);

-- Full-text search on canonical_text
CREATE INDEX IF NOT EXISTS idx_cd_fts
    ON platform.canonical_document
    USING GIN (to_tsvector('english', canonical_text));

-- ============================================================
-- 5. Document Chunk — RAG-ready chunks
-- ============================================================
CREATE TABLE IF NOT EXISTS platform.document_chunk (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_document_id   uuid NOT NULL REFERENCES platform.canonical_document(id) ON DELETE CASCADE,
    chunk_id                text NOT NULL UNIQUE,
    chunk_index             int NOT NULL DEFAULT 0,
    text                    text NOT NULL,
    metadata                jsonb NOT NULL DEFAULT '{}',
    token_count             int,
    embedding_status        text NOT NULL DEFAULT 'not_started',
    created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dc_canonical
    ON platform.document_chunk (canonical_document_id);
CREATE INDEX IF NOT EXISTS idx_dc_embedding
    ON platform.document_chunk (embedding_status);

-- ============================================================
-- 6. Digitalization Event Log — audit trail
-- ============================================================
CREATE TABLE IF NOT EXISTS platform.digitalization_event_log (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          uuid,
    manifest_id     uuid,
    event_type      text NOT NULL,
    status          text NOT NULL DEFAULT '',
    message         text NOT NULL DEFAULT '',
    details         jsonb NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_del_job
    ON platform.digitalization_event_log (job_id);
CREATE INDEX IF NOT EXISTS idx_del_manifest
    ON platform.digitalization_event_log (manifest_id);
CREATE INDEX IF NOT EXISTS idx_del_type
    ON platform.digitalization_event_log (event_type);
CREATE INDEX IF NOT EXISTS idx_del_created
    ON platform.digitalization_event_log (created_at);
