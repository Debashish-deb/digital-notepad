-- LUMI-W002: link vault assets to page registry.

ALTER TABLE platform.raw_asset_vault
  ADD COLUMN IF NOT EXISTS page_domain_id text REFERENCES platform.page_domain(page_domain_id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS page_section_id text REFERENCES platform.page_section(page_section_id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS mime_type text;

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_page_domain
  ON platform.raw_asset_vault (page_domain_id);

CREATE INDEX IF NOT EXISTS idx_raw_asset_vault_page_section
  ON platform.raw_asset_vault (page_section_id);
