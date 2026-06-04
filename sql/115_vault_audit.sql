-- LUMI-W020: vault audit trail.

CREATE TABLE IF NOT EXISTS platform.vault_audit_event (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id text,
  event_type text NOT NULL,
  actor text,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vault_audit_asset ON platform.vault_audit_event (asset_id);
CREATE INDEX IF NOT EXISTS idx_vault_audit_created ON platform.vault_audit_event (created_at DESC);
