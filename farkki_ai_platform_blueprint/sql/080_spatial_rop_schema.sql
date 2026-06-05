-- Create schema migrations for Clinical-Spatial Research Operating Platform (CS-ROP)

CREATE TABLE IF NOT EXISTS platform.project_extension (
  project_id uuid PRIMARY KEY REFERENCES core.project(project_id) ON DELETE CASCADE,
  project_short_title text,
  research_question text,
  project_type text NOT NULL DEFAULT 'spatial_profiling', -- 'spatial_profiling', 'clinical_trial', etc.
  priority text NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
  collaborators text[] NOT NULL DEFAULT '{}',
  ethics_approval_reference text,
  current_blockers text,
  next_actions text,
  project_summary text,
  latest_update text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.project_member (
  project_id uuid REFERENCES core.project(project_id) ON DELETE CASCADE,
  researcher_id uuid REFERENCES platform.researcher(researcher_id) ON DELETE CASCADE,
  role text NOT NULL DEFAULT 'researcher', -- 'PI', 'project_lead', 'bioinformatician', etc.
  project_access_level text NOT NULL DEFAULT 'read_write', -- 'read_only', 'read_write', 'admin'
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, researcher_id)
);

CREATE TABLE IF NOT EXISTS platform.notebook_entry (
  entry_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.project(project_id) ON DELETE CASCADE,
  sample_id uuid REFERENCES core.sample(sample_id) ON DELETE SET NULL,
  experiment_name text,
  pipeline_stage text,
  author_id uuid NOT NULL REFERENCES platform.researcher(researcher_id) ON DELETE CASCADE,
  title text NOT NULL,
  content text NOT NULL,
  conclusions text,
  issues_found text,
  decisions_made text,
  next_steps text,
  tags text[] NOT NULL DEFAULT '{}',
  entry_type text NOT NULL DEFAULT 'general_note', -- 'experiment_note', 'meeting_note', 'troubleshooting_note', etc.
  visibility_level text NOT NULL DEFAULT 'internal', -- 'public', 'internal', 'restricted'
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.folder_catalog (
  folder_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.project(project_id) ON DELETE CASCADE,
  sample_id uuid REFERENCES core.sample(sample_id) ON DELETE SET NULL,
  folder_name text NOT NULL,
  absolute_path text NOT NULL UNIQUE,
  relative_path text,
  storage_system text NOT NULL DEFAULT 'local workstation', -- 'local workstation', 'LUMI scratch', etc.
  os_type text NOT NULL DEFAULT 'linux', -- 'linux', 'macos', 'windows'
  location_type text NOT NULL DEFAULT 'active', -- 'active', 'scratch', 'archive'
  description text,
  pipeline_stage text,
  data_type text, -- 'raw images', 'segmentation masks', etc.
  file_count integer DEFAULT 0,
  total_size_bytes bigint DEFAULT 0,
  owner_id uuid REFERENCES platform.researcher(researcher_id) ON DELETE SET NULL,
  last_scanned timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.dataset_catalog (
  dataset_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.project(project_id) ON DELETE CASCADE,
  sample_id uuid REFERENCES core.sample(sample_id) ON DELETE SET NULL,
  dataset_name text NOT NULL,
  data_type text NOT NULL, -- 'OME-TIFF', 'CSV', 'AnnData', etc.
  format text NOT NULL,
  file_path text NOT NULL UNIQUE,
  file_size_bytes bigint,
  checksum text,
  pipeline_stage text,
  software_used text,
  version_used text,
  input_datasets jsonb NOT NULL DEFAULT '[]',
  output_datasets jsonb NOT NULL DEFAULT '[]',
  quality_status text NOT NULL DEFAULT 'pending_qc', -- 'pending_qc', 'approved', 'rejected'
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.pipeline_run (
  run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.project(project_id) ON DELETE CASCADE,
  sample_id uuid REFERENCES core.sample(sample_id) ON DELETE SET NULL,
  pipeline_stage text NOT NULL, -- 'Ashlar stitching', 'Mesmer segmentation', etc.
  command_used text,
  script_path text,
  config_path text,
  input_paths text[] NOT NULL DEFAULT '{}',
  output_paths text[] NOT NULL DEFAULT '{}',
  environment_info jsonb NOT NULL DEFAULT '{}', -- OS, conda env, container SIF, etc.
  start_time timestamptz NOT NULL DEFAULT now(),
  end_time timestamptz,
  duration_seconds integer,
  status text NOT NULL DEFAULT 'running', -- 'running', 'completed', 'failed'
  log_path text,
  error_summary text,
  qc_result text,
  notebook_entry_id uuid REFERENCES platform.notebook_entry(entry_id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.task (
  task_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.project(project_id) ON DELETE CASCADE,
  sample_id uuid REFERENCES core.sample(sample_id) ON DELETE SET NULL,
  assigned_to uuid REFERENCES platform.researcher(researcher_id) ON DELETE SET NULL,
  title text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'todo', -- 'todo', 'in_progress', 'blocked', 'done'
  priority text NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high'
  due_date date,
  related_notebook_entry_id uuid REFERENCES platform.notebook_entry(entry_id) ON DELETE SET NULL,
  related_pipeline_run_id uuid REFERENCES platform.pipeline_run(run_id) ON DELETE SET NULL,
  related_dataset_id uuid REFERENCES platform.dataset_catalog(dataset_id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.auto_log (
  log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES core.project(project_id) ON DELETE CASCADE,
  actor text NOT NULL DEFAULT 'system',
  event_type text NOT NULL, -- 'notebook_created', 'pipeline_completed', etc.
  description text NOT NULL,
  linked_object_type text,
  linked_object_id uuid,
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
