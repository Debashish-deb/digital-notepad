-- Raw Knowledge Vault ingestion engine (resumable scan, metadata_json, checkpoints).

ALTER TABLE platform.raw_asset_vault
  ADD COLUMN IF NOT EXISTS metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_extraction
  ON platform.raw_asset_vault (extraction_status);

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_vector
  ON platform.raw_asset_vault (vector_status);

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_uncategorized
  ON platform.raw_asset_vault (page_domain_id)
  WHERE page_domain_id IS NULL;

CREATE TABLE IF NOT EXISTS platform.vault_scan_checkpoint (
  checkpoint_id text PRIMARY KEY,
  scan_root text NOT NULL,
  project_hint text,
  last_logical_path text,
  files_processed integer NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'running',
  manifest_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  job_id uuid REFERENCES platform.ingestion_job(job_id) ON DELETE SET NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vault_scan_checkpoint_status
  ON platform.vault_scan_checkpoint (status, updated_at DESC);
