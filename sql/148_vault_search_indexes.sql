-- Vault search reliability indexes (Phase: semantic + Postgres-authoritative search).

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_filename_lower
  ON platform.raw_asset_vault (lower(filename));

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_duplicate_status
  ON platform.raw_asset_vault (
    (COALESCE(metadata_json->>'duplicate_status', 'unique'))
  );

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_inventory_active
  ON platform.raw_asset_vault (
    (COALESCE(metadata_json->>'inventory_active', 'true'))
  );

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_metadata_gin
  ON platform.raw_asset_vault USING gin (metadata_json);
