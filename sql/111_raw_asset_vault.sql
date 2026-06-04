-- Raw knowledge vault (Phase 2/3) — mirrors docs/11 asset survey model.
-- original_path is server-side only; API must never return it.

CREATE TABLE IF NOT EXISTS platform.raw_asset_vault (
  asset_id text PRIMARY KEY,
  storage_provider text NOT NULL,
  logical_path text NOT NULL,
  filename text NOT NULL,
  extension text NOT NULL DEFAULT '',
  size_bytes bigint NOT NULL DEFAULT 0,
  checksum_sha256 text,
  asset_type text NOT NULL DEFAULT 'other',
  domain text,
  project_hint text,
  section_hint text,
  sensitivity_level text NOT NULL DEFAULT 'unknown',
  assignment_confidence numeric(4, 2) NOT NULL DEFAULT 0,
  sensitivity_confidence numeric(4, 2) NOT NULL DEFAULT 0,
  review_status text NOT NULL DEFAULT 'raw',
  vector_status text NOT NULL DEFAULT 'not_evaluated',
  graph_status text NOT NULL DEFAULT 'not_asserted',
  extraction_status text NOT NULL DEFAULT 'not_started',
  original_path text,
  provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
  modified_at timestamptz,
  indexed_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_logical_path
  ON platform.raw_asset_vault (logical_path);

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_checksum
  ON platform.raw_asset_vault (checksum_sha256)
  WHERE checksum_sha256 IS NOT NULL AND checksum_sha256 <> '';

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_review
  ON platform.raw_asset_vault (review_status, assignment_confidence);

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_domain
  ON platform.raw_asset_vault (domain);
