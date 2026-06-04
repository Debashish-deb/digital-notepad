-- LUMI-W050/W100/W130: user registry, ingestion and vectorization jobs, review tasks.

CREATE TABLE IF NOT EXISTS platform.allowed_email (
  email text PRIMARY KEY,
  status text NOT NULL DEFAULT 'approved',
  approved_by text,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.registration_request (
  request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL,
  display_name text,
  status text NOT NULL DEFAULT 'pending',
  requested_at timestamptz NOT NULL DEFAULT now(),
  reviewed_by text,
  reviewed_at timestamptz
);

CREATE TABLE IF NOT EXISTS platform.ingestion_job (
  job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type text NOT NULL,
  status text NOT NULL DEFAULT 'queued',
  started_at timestamptz,
  finished_at timestamptz,
  items_total integer DEFAULT 0,
  items_processed integer DEFAULT 0,
  error_summary text,
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.vectorization_job (
  job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id text,
  document_id uuid,
  status text NOT NULL DEFAULT 'queued',
  blocked_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE TABLE IF NOT EXISTS platform.review_task (
  task_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id text NOT NULL,
  task_type text NOT NULL DEFAULT 'classification_review',
  status text NOT NULL DEFAULT 'open',
  assignment_confidence numeric(4, 2),
  sensitivity_level text,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_review_task_status ON platform.review_task (status);
