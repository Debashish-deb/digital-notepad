-- Agent audit log for category-based orchestration (append-only; optional migration)

CREATE TABLE IF NOT EXISTS platform.agent_audit_log (
  audit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL,
  category text NOT NULL,
  mode text NOT NULL DEFAULT 'balanced',
  user_email text,
  user_role text,
  source_buckets text,
  source_counts jsonb NOT NULL DEFAULT '{}'::jsonb,
  latency_ms integer,
  provider text,
  model text,
  grounding_outcome text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_audit_log_created
  ON platform.agent_audit_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_audit_log_run
  ON platform.agent_audit_log (run_id);

CREATE INDEX IF NOT EXISTS idx_agent_audit_log_category
  ON platform.agent_audit_log (category, created_at DESC);
