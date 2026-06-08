-- Unified taxonomy assignments (Phase 4)
CREATE SCHEMA IF NOT EXISTS platform;

CREATE TABLE IF NOT EXISTS platform.taxonomy_assignment (
    asset_id          TEXT NOT NULL,
    taxonomy_key      TEXT NOT NULL,
    source            TEXT NOT NULL,
    confidence        REAL DEFAULT 1.0,
    assigned_at       TIMESTAMPTZ DEFAULT now(),
    assigned_by       TEXT,
    superseded_at     TIMESTAMPTZ,
    PRIMARY KEY (asset_id, taxonomy_key, source)
);

CREATE INDEX IF NOT EXISTS idx_taxonomy_key
    ON platform.taxonomy_assignment (taxonomy_key)
    WHERE superseded_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_taxonomy_asset_active
    ON platform.taxonomy_assignment (asset_id)
    WHERE superseded_at IS NULL;
