-- Storage architecture consolidation (117): objects index, provider policy, ingestion hooks.
-- Replaces standalone 117_storage_objects.sql on fresh installs (idempotent).

CREATE TABLE IF NOT EXISTS platform.storage_objects (
  object_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  storage_root_id text NOT NULL REFERENCES platform.storage_root(storage_root_id),
  storage_provider text NOT NULL,
  logical_path text NOT NULL,
  relative_path text NOT NULL DEFAULT '',
  object_type text NOT NULL DEFAULT 'file',
  size_bytes bigint,
  etag text,
  checksum_sha256 text,
  mime_type text,
  scan_status text NOT NULL DEFAULT 'discovered',
  conflict_flags jsonb NOT NULL DEFAULT '[]'::jsonb,
  needs_user_decision boolean NOT NULL DEFAULT false,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (storage_provider, logical_path)
);

CREATE INDEX IF NOT EXISTS idx_storage_objects_provider
  ON platform.storage_objects (storage_provider, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_storage_objects_root
  ON platform.storage_objects (storage_root_id);

CREATE INDEX IF NOT EXISTS idx_storage_objects_needs_decision
  ON platform.storage_objects (needs_user_decision)
  WHERE needs_user_decision = true;

-- Active storage_provider values (documented; not enforced by CHECK until vault backfill complete):
-- datacloud_webdav, pdrive_smb, supabase_storage, local_database_mirror, local_dev, unknown
-- deprecated: cloudflare_r2

UPDATE platform.storage_root
SET description = 'DEPRECATED — removed from architecture',
    role = 'deprecated',
    configured = false
WHERE storage_root_id = 'cloudflare_r2';

INSERT INTO platform.storage_root (storage_root_id, provider_id, role, root_logical_path, configured, description)
VALUES (
  'supabase_storage',
  'supabase_storage',
  'small_files_previews',
  'supabase://assets',
  false,
  'Supabase Storage — avatars, UI assets, small previews only'
)
ON CONFLICT (storage_root_id) DO NOTHING;

-- Link ingestion jobs to storage scans (optional metadata)
COMMENT ON TABLE platform.storage_objects IS
  'Logical index from WebDAV/P-drive scans; blobs remain on external storage.';
