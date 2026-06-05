CREATE TABLE IF NOT EXISTS security.user_account (
  user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  external_subject text UNIQUE,
  email text,
  display_name text,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS security.role (
  role_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  role_name text NOT NULL UNIQUE,
  description text
);

CREATE TABLE IF NOT EXISTS security.user_role (
  user_id uuid REFERENCES security.user_account(user_id) ON DELETE CASCADE,
  role_id uuid REFERENCES security.role(role_id) ON DELETE CASCADE,
  project_id uuid REFERENCES core.project(project_id) ON DELETE CASCADE,
  granted_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(user_id, role_id, project_id)
);

CREATE TABLE IF NOT EXISTS security.project_access_policy (
  policy_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.project(project_id) ON DELETE CASCADE,
  role_id uuid NOT NULL REFERENCES security.role(role_id) ON DELETE CASCADE,
  max_sensitivity core.sensitivity_level NOT NULL,
  can_run_analysis boolean NOT NULL DEFAULT false,
  can_export boolean NOT NULL DEFAULT false,
  can_manage_project boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_id, role_id)
);

CREATE TABLE IF NOT EXISTS rag.document_source (
  document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_code text NOT NULL UNIQUE,
  title text NOT NULL,
  source_type text NOT NULL,
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  source_file_id uuid REFERENCES files.file_object(file_id) ON DELETE SET NULL,
  external_url text,
  owner text,
  sensitivity_level core.sensitivity_level NOT NULL DEFAULT 'internal',
  status core.record_status NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rag.document_chunk (
  chunk_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES rag.document_source(document_id) ON DELETE CASCADE,
  chunk_index integer NOT NULL,
  chunk_uid text NOT NULL UNIQUE,
  section_path text,
  chunk_text text NOT NULL,
  token_count integer,
  entities jsonb NOT NULL DEFAULT '[]',
  sensitivity_level core.sensitivity_level NOT NULL DEFAULT 'internal',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS rag.embedding_job (
  embedding_job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_code text NOT NULL UNIQUE,
  embedding_model text NOT NULL,
  embedding_dimension integer NOT NULL,
  distance_metric text NOT NULL,
  collection_name text NOT NULL,
  started_at timestamptz,
  finished_at timestamptz,
  status core.run_status NOT NULL DEFAULT 'queued',
  config jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rag.vector_point_registry (
  vector_point_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  embedding_job_id uuid REFERENCES rag.embedding_job(embedding_job_id) ON DELETE SET NULL,
  collection_name text NOT NULL,
  qdrant_point_id text NOT NULL,
  source_type text NOT NULL,
  source_uuid uuid,
  chunk_id uuid REFERENCES rag.document_chunk(chunk_id) ON DELETE SET NULL,
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  sample_id uuid REFERENCES core.sample(sample_id) ON DELETE SET NULL,
  embedding_model text NOT NULL,
  embedding_dimension integer NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  status core.record_status NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(collection_name, qdrant_point_id)
);

CREATE TABLE IF NOT EXISTS rag.retrieval_trace (
  retrieval_trace_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES security.user_account(user_id) ON DELETE SET NULL,
  question text NOT NULL,
  normalized_query jsonb NOT NULL DEFAULT '{}',
  collections_searched text[],
  filters jsonb NOT NULL DEFAULT '{}',
  retrieved_points jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rag.answer_trace (
  answer_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  retrieval_trace_id uuid REFERENCES rag.retrieval_trace(retrieval_trace_id) ON DELETE SET NULL,
  user_id uuid REFERENCES security.user_account(user_id) ON DELETE SET NULL,
  question text NOT NULL,
  answer_text text NOT NULL,
  model_name text,
  model_version text,
  source_summary jsonb NOT NULL DEFAULT '{}',
  limitations jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kg.entity_registry (
  entity_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type text NOT NULL,
  canonical_name text NOT NULL,
  display_name text,
  external_ids jsonb NOT NULL DEFAULT '{}',
  aliases text[] DEFAULT '{}',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(entity_type, canonical_name)
);

CREATE TABLE IF NOT EXISTS kg.assertion (
  assertion_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_entity_id uuid REFERENCES kg.entity_registry(entity_id) ON DELETE CASCADE,
  predicate text NOT NULL,
  object_entity_id uuid REFERENCES kg.entity_registry(entity_id) ON DELETE CASCADE,
  confidence numeric,
  evidence_level text,
  source_type text,
  source_id uuid,
  notes text,
  status core.record_status NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit.event_log (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_time timestamptz NOT NULL DEFAULT now(),
  user_id uuid REFERENCES security.user_account(user_id) ON DELETE SET NULL,
  action text NOT NULL,
  resource_type text,
  resource_id uuid,
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  sensitivity_level core.sensitivity_level,
  success boolean NOT NULL DEFAULT true,
  client_info jsonb NOT NULL DEFAULT '{}',
  details jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS audit.tool_execution_log (
  tool_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES security.user_account(user_id) ON DELETE SET NULL,
  tool_name text NOT NULL,
  tool_version text,
  input_summary jsonb NOT NULL DEFAULT '{}',
  output_summary jsonb NOT NULL DEFAULT '{}',
  started_at timestamptz,
  finished_at timestamptz,
  status core.run_status NOT NULL DEFAULT 'queued',
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now()
);
