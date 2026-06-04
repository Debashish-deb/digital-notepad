-- Phase 4: Analysis run registry (survival, group comparison, similarity)

CREATE SCHEMA IF NOT EXISTS platform;

CREATE TABLE IF NOT EXISTS platform.analysis_run (
  analysis_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  run_code text NOT NULL UNIQUE,
  analysis_type text NOT NULL, -- survival | group_compare | feature_similarity | spatial_neighborhood
  title text,
  parameters jsonb NOT NULL DEFAULT '{}',
  status text NOT NULL DEFAULT 'completed',
  results jsonb NOT NULL DEFAULT '{}',
  artifact_paths jsonb NOT NULL DEFAULT '[]',
  requested_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_analysis_run_project ON platform.analysis_run(project_id);
CREATE INDEX IF NOT EXISTS idx_analysis_run_type ON platform.analysis_run(analysis_type);
