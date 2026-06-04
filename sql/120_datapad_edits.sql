-- Data Pad edit audit trail (section document saves, restores, AI applies).

CREATE TABLE IF NOT EXISTS platform.datapad_edit_log (
  edit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_code text NOT NULL,
  relative_path text NOT NULL,
  event_type text NOT NULL,
  actor text,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_datapad_edit_project ON platform.datapad_edit_log (project_code);
CREATE INDEX IF NOT EXISTS idx_datapad_edit_path ON platform.datapad_edit_log (relative_path);
CREATE INDEX IF NOT EXISTS idx_datapad_edit_created ON platform.datapad_edit_log (created_at DESC);
