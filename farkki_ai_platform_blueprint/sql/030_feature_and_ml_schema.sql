CREATE TABLE IF NOT EXISTS features.feature_definition (
  feature_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  feature_name text NOT NULL UNIQUE,
  display_name text,
  feature_group text NOT NULL,
  entity_level text NOT NULL,
  data_type text NOT NULL,
  unit text,
  source_modality text,
  calculation_method text NOT NULL,
  required_inputs jsonb NOT NULL DEFAULT '[]',
  parameters jsonb NOT NULL DEFAULT '{}',
  version text NOT NULL DEFAULT '1.0.0',
  owner text,
  status core.record_status NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS features.feature_matrix (
  feature_matrix_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  matrix_code text NOT NULL UNIQUE,
  matrix_name text,
  matrix_version text NOT NULL,
  entity_level text NOT NULL,
  row_entity_type text NOT NULL,
  row_count bigint,
  feature_count integer,
  file_id uuid REFERENCES files.file_object(file_id) ON DELETE SET NULL,
  source_pipeline_run_code text,
  inclusion_criteria text,
  exclusion_criteria text,
  qc_status text DEFAULT 'unknown',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS features.feature_value (
  feature_value_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  feature_matrix_id uuid REFERENCES features.feature_matrix(feature_matrix_id) ON DELETE CASCADE,
  feature_id uuid NOT NULL REFERENCES features.feature_definition(feature_id) ON DELETE CASCADE,
  entity_type text NOT NULL,
  entity_uuid uuid,
  entity_code text,
  value_numeric numeric,
  value_text text,
  value_boolean boolean,
  value_json jsonb,
  qc_status text DEFAULT 'unknown',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clinical.variable_dictionary (
  variable_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  variable_name text NOT NULL UNIQUE,
  display_name text,
  data_type text NOT NULL,
  unit text,
  allowed_values jsonb,
  missing_value_codes text[] DEFAULT '{}',
  valid_min numeric,
  valid_max numeric,
  definition text,
  curation_rule text,
  sensitivity_level core.sensitivity_level NOT NULL DEFAULT 'restricted',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clinical.patient_clinical_summary (
  patient_id uuid PRIMARY KEY REFERENCES core.patient(patient_id) ON DELETE CASCADE,
  histology text,
  stage text,
  grade text,
  diagnosis_age numeric,
  hrd_status text,
  brca_status text,
  platinum_response text,
  parpi_exposure boolean,
  parpi_line text,
  pfs_months numeric,
  pfi_months numeric,
  os_months numeric,
  progression_event boolean,
  death_event boolean,
  residual_disease text,
  curation_version text,
  source_file_id uuid REFERENCES files.file_object(file_id) ON DELETE SET NULL,
  qc_status text DEFAULT 'unknown',
  metadata jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clinical.clinical_observation (
  observation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id uuid REFERENCES core.patient(patient_id) ON DELETE CASCADE,
  sample_id uuid REFERENCES core.sample(sample_id) ON DELETE CASCADE,
  variable_id uuid NOT NULL REFERENCES clinical.variable_dictionary(variable_id) ON DELETE CASCADE,
  value_text text,
  value_numeric numeric,
  value_date date,
  value_boolean boolean,
  value_json jsonb,
  unit text,
  source_file_id uuid REFERENCES files.file_object(file_id) ON DELETE SET NULL,
  source_column text,
  curation_status text DEFAULT 'uncurated',
  confidence numeric,
  observed_at date,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ml.model_registry (
  model_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  model_code text NOT NULL UNIQUE,
  model_name text NOT NULL,
  model_family text,
  intended_use text,
  owner text,
  status core.record_status NOT NULL DEFAULT 'draft',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ml.training_run (
  training_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  model_code text NOT NULL,
  analysis_dataset_code text,
  run_code text NOT NULL UNIQUE,
  split_strategy text,
  cv_design text,
  target_variable text,
  class_balance jsonb,
  started_at timestamptz,
  finished_at timestamptz,
  status core.run_status NOT NULL DEFAULT 'queued',
  metrics jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
