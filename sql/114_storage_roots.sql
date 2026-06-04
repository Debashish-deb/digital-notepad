-- LUMI-W010: persisted storage root configuration (no secrets in API).

CREATE TABLE IF NOT EXISTS platform.storage_root (
  storage_root_id text PRIMARY KEY,
  provider_id text NOT NULL,
  role text NOT NULL,
  root_logical_path text,
  configured boolean NOT NULL DEFAULT false,
  description text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO platform.storage_root (storage_root_id, provider_id, role, root_logical_path, configured, description) VALUES
  ('datacloud_webdav', 'datacloud_webdav', 'primary_research', '/farkkila/LAB-ASSISTANT-PLATFORM', false,
   'University of Helsinki DataCloud WebDAV canonical root'),
  ('pdrive_smb', 'pdrive_smb', 'secondary_research', NULL, false, 'P-drive SMB shared lab storage'),
  ('cloudflare_r2', 'cloudflare_r2', 'previews_only', NULL, false, 'Cloudflare R2 previews only'),
  ('supabase_postgres', 'supabase_postgres', 'metadata_permissions_vectors', NULL, false, 'Supabase PostgreSQL metadata'),
  ('local_database_mirror', 'local_database_mirror', 'evidence_mirror', 'database/', false, 'Local dev evidence mirror')
ON CONFLICT (storage_root_id) DO NOTHING;
