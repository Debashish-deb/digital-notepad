-- Search platform: query log + lightweight full-text helpers (portable; optional on dev)

CREATE TABLE IF NOT EXISTS platform.search_query_log (
  query_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  query_text text NOT NULL,
  mode text NOT NULL DEFAULT 'hybrid',
  scopes text,
  project_code text,
  hit_count integer NOT NULL DEFAULT 0,
  user_email text,
  user_role text,
  duration_ms integer,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_search_query_log_created
  ON platform.search_query_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_query_log_user
  ON platform.search_query_log (user_email, created_at DESC);

-- Trigram extension for better keyword search (optional — ignore if unavailable)
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
EXCEPTION
  WHEN insufficient_privilege THEN
    RAISE NOTICE 'pg_trgm not installed — ILIKE search still works';
END $$;
