CREATE TABLE IF NOT EXISTS core.project (
  project_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_code text NOT NULL UNIQUE,
  project_name text NOT NULL,
  short_description text,
  long_description text,
  disease_focus text,
  principal_investigator text,
  project_lead text,
  start_date date,
  end_date date,
  default_sensitivity core.sensitivity_level NOT NULL DEFAULT 'internal',
  status core.record_status NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.cohort (
  cohort_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES core.project(project_id) ON DELETE CASCADE,
  cohort_code text NOT NULL,
  cohort_name text NOT NULL,
  cohort_description text,
  inclusion_criteria text,
  exclusion_criteria text,
  source_system text,
  status core.record_status NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_id, cohort_code)
);

CREATE TABLE IF NOT EXISTS core.patient (
  patient_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_code text NOT NULL UNIQUE,
  source_system text,
  diagnosis_year integer,
  birth_year_bin text,
  sex_at_birth_code text,
  disease_label text,
  sensitivity_level core.sensitivity_level NOT NULL DEFAULT 'restricted',
  status core.record_status NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.patient_cohort_membership (
  patient_id uuid REFERENCES core.patient(patient_id) ON DELETE CASCADE,
  cohort_id uuid REFERENCES core.cohort(cohort_id) ON DELETE CASCADE,
  membership_status text NOT NULL DEFAULT 'included',
  inclusion_notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(patient_id, cohort_id)
);

CREATE TABLE IF NOT EXISTS core.specimen (
  specimen_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id uuid NOT NULL REFERENCES core.patient(patient_id) ON DELETE CASCADE,
  specimen_code text NOT NULL UNIQUE,
  anatomical_site text,
  anatomical_site_detail text,
  collection_timepoint text,
  surgery_type text,
  treatment_context text,
  block_id text,
  section_id text,
  collection_year integer,
  sensitivity_level core.sensitivity_level NOT NULL DEFAULT 'restricted',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.sample (
  sample_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id uuid REFERENCES core.patient(patient_id) ON DELETE SET NULL,
  specimen_id uuid REFERENCES core.specimen(specimen_id) ON DELETE SET NULL,
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  cohort_id uuid REFERENCES core.cohort(cohort_id) ON DELETE SET NULL,
  sample_code text NOT NULL UNIQUE,
  sample_name text,
  sample_type text,
  anatomical_site text,
  timepoint text,
  batch_code text,
  qc_status text DEFAULT 'unknown',
  sensitivity_level core.sensitivity_level NOT NULL DEFAULT 'restricted',
  status core.record_status NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.marker (
  marker_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name text NOT NULL UNIQUE,
  display_name text,
  marker_type text,
  gene_symbol text,
  protein_name text,
  description text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.marker_alias (
  marker_alias_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  marker_id uuid NOT NULL REFERENCES core.marker(marker_id) ON DELETE CASCADE,
  alias text NOT NULL,
  alias_type text,
  source text,
  UNIQUE(marker_id, alias)
);

CREATE TABLE IF NOT EXISTS core.cell_type (
  cell_type_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name text NOT NULL UNIQUE,
  display_name text,
  parent_cell_type_id uuid REFERENCES core.cell_type(cell_type_id),
  description text,
  created_at timestamptz NOT NULL DEFAULT now()
);
