-- Phase 11 — continuous quality evaluation run history.

CREATE TABLE IF NOT EXISTS platform.quality_eval_run (
  run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_at timestamptz NOT NULL DEFAULT now(),
  host text NOT NULL DEFAULT '',
  git_ref text,
  trigger_source text NOT NULL DEFAULT 'manual',
  status text NOT NULL CHECK (status IN ('pass', 'warn', 'fail')),
  composite_score numeric(5, 2),
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  gates jsonb NOT NULL DEFAULT '{}'::jsonb,
  regressions jsonb NOT NULL DEFAULT '[]'::jsonb,
  artifacts jsonb NOT NULL DEFAULT '{}'::jsonb,
  duration_ms integer NOT NULL DEFAULT 0,
  notes text
);

CREATE INDEX IF NOT EXISTS idx_quality_eval_run_at
  ON platform.quality_eval_run (run_at DESC);

CREATE INDEX IF NOT EXISTS idx_quality_eval_status
  ON platform.quality_eval_run (status, run_at DESC);
