-- Project folder digitalization layer (raw knowledge before RAG/vectors).

CREATE TABLE IF NOT EXISTS platform.project_candidates (
  project_candidate_id text PRIMARY KEY,
  storage_root_id text NOT NULL DEFAULT 'lab_storage_root',
  project_name text NOT NULL,
  project_path text NOT NULL,
  relative_path text NOT NULL DEFAULT '',
  folder_count integer NOT NULL DEFAULT 0,
  file_count integer NOT NULL DEFAULT 0,
  document_count integer NOT NULL DEFAULT 0,
  data_count integer NOT NULL DEFAULT 0,
  script_count integer NOT NULL DEFAULT 0,
  image_count integer NOT NULL DEFAULT 0,
  log_count integer NOT NULL DEFAULT 0,
  project_status text NOT NULL DEFAULT 'unreviewed',
  ai_category_status text NOT NULL DEFAULT 'pending',
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.folder_assets (
  folder_id text PRIMARY KEY,
  storage_root_id text NOT NULL DEFAULT 'lab_storage_root',
  absolute_path text NOT NULL,
  relative_path text NOT NULL,
  folder_name text NOT NULL,
  parent_path text,
  project_candidate_id text REFERENCES platform.project_candidates(project_candidate_id) ON DELETE SET NULL,
  folder_depth integer NOT NULL DEFAULT 0,
  file_count integer NOT NULL DEFAULT 0,
  subfolder_count integer NOT NULL DEFAULT 0,
  modified_at timestamptz,
  storage_provider text NOT NULL DEFAULT 'lab_storage_root',
  scan_status text NOT NULL DEFAULT 'scanned',
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.knowledge_assets (
  asset_id text PRIMARY KEY REFERENCES platform.raw_asset_vault(asset_id) ON DELETE CASCADE,
  storage_root_id text NOT NULL DEFAULT 'lab_storage_root',
  absolute_path text NOT NULL,
  relative_path text NOT NULL,
  filename text NOT NULL,
  extension text NOT NULL DEFAULT '',
  file_size bigint NOT NULL DEFAULT 0,
  modified_at timestamptz,
  detected_type text NOT NULL DEFAULT 'unknown',
  project_candidate_id text REFERENCES platform.project_candidates(project_candidate_id) ON DELETE SET NULL,
  sample_candidate_id text,
  pipeline_stage_guess text,
  user_category text,
  ai_category text,
  confidence_score numeric(5, 2),
  ingestion_status text NOT NULL DEFAULT 'registered',
  extraction_status text NOT NULL DEFAULT 'not_started',
  review_status text NOT NULL DEFAULT 'needs_review',
  embedding_status text NOT NULL DEFAULT 'disabled',
  embedding_model text,
  embedded_at timestamptz,
  chunking_status text NOT NULL DEFAULT 'not_started',
  chunk_count integer NOT NULL DEFAULT 0,
  error_message text,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.extracted_texts (
  text_id bigserial PRIMARY KEY,
  asset_id text NOT NULL REFERENCES platform.knowledge_assets(asset_id) ON DELETE CASCADE,
  raw_text text,
  cleaned_text text,
  extraction_method text,
  quality_score numeric(5, 2),
  char_count integer NOT NULL DEFAULT 0,
  word_count integer NOT NULL DEFAULT 0,
  language_guess text,
  ocr_needed boolean NOT NULL DEFAULT false,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.extracted_tables (
  table_id bigserial PRIMARY KEY,
  asset_id text NOT NULL REFERENCES platform.knowledge_assets(asset_id) ON DELETE CASCADE,
  sheet_name text,
  row_count integer,
  column_count integer,
  column_names jsonb NOT NULL DEFAULT '[]'::jsonb,
  column_types jsonb NOT NULL DEFAULT '{}'::jsonb,
  preview_rows jsonb NOT NULL DEFAULT '[]'::jsonb,
  missing_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  schema_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.script_metadata (
  script_id bigserial PRIMARY KEY,
  asset_id text NOT NULL REFERENCES platform.knowledge_assets(asset_id) ON DELETE CASCADE,
  language text,
  imports jsonb NOT NULL DEFAULT '[]'::jsonb,
  functions jsonb NOT NULL DEFAULT '[]'::jsonb,
  classes jsonb NOT NULL DEFAULT '[]'::jsonb,
  input_paths jsonb NOT NULL DEFAULT '[]'::jsonb,
  output_paths jsonb NOT NULL DEFAULT '[]'::jsonb,
  cli_args jsonb NOT NULL DEFAULT '[]'::jsonb,
  software_names jsonb NOT NULL DEFAULT '[]'::jsonb,
  pipeline_stage_guess text,
  summary_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.log_summaries (
  log_id bigserial PRIMARY KEY,
  asset_id text NOT NULL REFERENCES platform.knowledge_assets(asset_id) ON DELETE CASCADE,
  job_id text,
  software_name text,
  error_messages jsonb NOT NULL DEFAULT '[]'::jsonb,
  warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
  status_guess text NOT NULL DEFAULT 'unknown',
  failed_command text,
  output_paths jsonb NOT NULL DEFAULT '[]'::jsonb,
  pipeline_stage_guess text,
  summary_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.entity_candidates (
  entity_id bigserial PRIMARY KEY,
  asset_id text REFERENCES platform.knowledge_assets(asset_id) ON DELETE CASCADE,
  project_candidate_id text REFERENCES platform.project_candidates(project_candidate_id) ON DELETE CASCADE,
  entity_type text NOT NULL,
  entity_value text NOT NULL,
  confidence_score numeric(5, 2) NOT NULL DEFAULT 0.5,
  review_status text NOT NULL DEFAULT 'needs_review',
  source_field text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.relationship_candidates (
  relationship_id bigserial PRIMARY KEY,
  from_asset_id text REFERENCES platform.knowledge_assets(asset_id) ON DELETE CASCADE,
  to_asset_id text REFERENCES platform.knowledge_assets(asset_id) ON DELETE SET NULL,
  relation_type text NOT NULL,
  confidence_score numeric(5, 2) NOT NULL DEFAULT 0.5,
  review_status text NOT NULL DEFAULT 'needs_review',
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.digitalization_runs (
  run_id text PRIMARY KEY,
  mode text NOT NULL,
  storage_root text NOT NULL,
  project_name text,
  status text NOT NULL DEFAULT 'running',
  dry_run boolean NOT NULL DEFAULT false,
  report_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE TABLE IF NOT EXISTS platform.digitalization_errors (
  error_id bigserial PRIMARY KEY,
  run_id text REFERENCES platform.digitalization_runs(run_id) ON DELETE CASCADE,
  asset_id text,
  relative_path text,
  error_message text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_assets_project ON platform.knowledge_assets (project_candidate_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_assets_review ON platform.knowledge_assets (review_status, extraction_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_assets_category ON platform.knowledge_assets (user_category, ai_category);
CREATE INDEX IF NOT EXISTS idx_extracted_texts_asset ON platform.extracted_texts (asset_id);
CREATE INDEX IF NOT EXISTS idx_extracted_tables_asset ON platform.extracted_tables (asset_id);
CREATE INDEX IF NOT EXISTS idx_entity_candidates_type ON platform.entity_candidates (entity_type, entity_value);
