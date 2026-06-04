CREATE TABLE IF NOT EXISTS files.file_object (
  file_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  storage_backend text NOT NULL,
  uri text NOT NULL,
  relative_path text,
  file_name text NOT NULL,
  file_extension text,
  media_type text,
  file_role text,
  size_bytes bigint,
  sha256 text,
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  sample_id uuid REFERENCES core.sample(sample_id) ON DELETE SET NULL,
  sensitivity_level core.sensitivity_level NOT NULL DEFAULT 'internal',
  status core.record_status NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(storage_backend, uri)
);

CREATE TABLE IF NOT EXISTS files.dataset_snapshot (
  snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  snapshot_code text NOT NULL,
  snapshot_name text,
  root_uri text,
  description text,
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_id, snapshot_code)
);

CREATE TABLE IF NOT EXISTS assay.assay_run (
  assay_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  cohort_id uuid REFERENCES core.cohort(cohort_id) ON DELETE SET NULL,
  assay_run_code text NOT NULL UNIQUE,
  assay_type text NOT NULL,
  platform text,
  batch_code text,
  operator_name text,
  protocol_name text,
  protocol_version text,
  run_date date,
  status core.run_status NOT NULL DEFAULT 'queued',
  config jsonb NOT NULL DEFAULT '{}',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assay.sample_assay (
  sample_assay_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sample_id uuid NOT NULL REFERENCES core.sample(sample_id) ON DELETE CASCADE,
  assay_run_id uuid NOT NULL REFERENCES assay.assay_run(assay_run_id) ON DELETE CASCADE,
  sample_role text DEFAULT 'primary',
  qc_status text DEFAULT 'unknown',
  metadata jsonb NOT NULL DEFAULT '{}',
  UNIQUE(sample_id, assay_run_id)
);

CREATE TABLE IF NOT EXISTS assay.panel (
  panel_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  panel_code text NOT NULL UNIQUE,
  panel_name text NOT NULL,
  assay_type text NOT NULL,
  version text,
  description text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assay.panel_marker (
  panel_id uuid REFERENCES assay.panel(panel_id) ON DELETE CASCADE,
  marker_id uuid REFERENCES core.marker(marker_id) ON DELETE CASCADE,
  marker_order integer,
  is_required boolean DEFAULT true,
  metadata jsonb NOT NULL DEFAULT '{}',
  PRIMARY KEY(panel_id, marker_id)
);

CREATE TABLE IF NOT EXISTS assay.channel_map (
  channel_map_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assay_run_id uuid REFERENCES assay.assay_run(assay_run_id) ON DELETE CASCADE,
  panel_id uuid REFERENCES assay.panel(panel_id) ON DELETE SET NULL,
  channel_map_code text NOT NULL UNIQUE,
  source_file_id uuid REFERENCES files.file_object(file_id) ON DELETE SET NULL,
  version text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assay.channel (
  channel_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_map_id uuid NOT NULL REFERENCES assay.channel_map(channel_map_id) ON DELETE CASCADE,
  channel_index integer NOT NULL,
  channel_name text NOT NULL,
  marker_id uuid REFERENCES core.marker(marker_id) ON DELETE SET NULL,
  round_number integer,
  cycle_number integer,
  is_dapi boolean NOT NULL DEFAULT false,
  is_background boolean NOT NULL DEFAULT false,
  is_failed boolean NOT NULL DEFAULT false,
  antibody_clone text,
  fluorophore text,
  exposure_ms numeric,
  metadata jsonb NOT NULL DEFAULT '{}',
  UNIQUE(channel_map_id, channel_index)
);

CREATE TABLE IF NOT EXISTS spatial.image_processing_run (
  image_processing_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  pipeline_run_code text NOT NULL UNIQUE,
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  assay_run_id uuid REFERENCES assay.assay_run(assay_run_id) ON DELETE SET NULL,
  pipeline_name text NOT NULL,
  pipeline_version text,
  git_commit text,
  container_image text,
  container_digest text,
  executor text,
  started_at timestamptz,
  finished_at timestamptz,
  status core.run_status NOT NULL DEFAULT 'queued',
  config jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS spatial.segmentation_run (
  segmentation_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  image_processing_run_id uuid REFERENCES spatial.image_processing_run(image_processing_run_id) ON DELETE SET NULL,
  sample_id uuid NOT NULL REFERENCES core.sample(sample_id) ON DELETE CASCADE,
  input_image_file_id uuid REFERENCES files.file_object(file_id) ON DELETE SET NULL,
  mask_file_id uuid REFERENCES files.file_object(file_id) ON DELETE SET NULL,
  method text NOT NULL,
  method_version text,
  compartment text NOT NULL,
  nuclear_channel_index integer,
  membrane_channel_index integer,
  model_name text,
  model_version text,
  tile_size integer,
  overlap_fraction numeric,
  mpp numeric,
  cell_count bigint,
  max_label bigint,
  status core.run_status NOT NULL DEFAULT 'queued',
  qc_metrics jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS spatial.quantification_run (
  quantification_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  image_processing_run_id uuid REFERENCES spatial.image_processing_run(image_processing_run_id) ON DELETE SET NULL,
  sample_id uuid NOT NULL REFERENCES core.sample(sample_id) ON DELETE CASCADE,
  segmentation_run_id uuid REFERENCES spatial.segmentation_run(segmentation_run_id) ON DELETE SET NULL,
  output_table_file_id uuid REFERENCES files.file_object(file_id) ON DELETE SET NULL,
  channel_map_id uuid REFERENCES assay.channel_map(channel_map_id) ON DELETE SET NULL,
  method text,
  method_version text,
  cell_count bigint,
  marker_columns text[],
  morphology_columns text[],
  coordinate_columns text[],
  qc_status text DEFAULT 'unknown',
  qc_metrics jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS spatial.cell_table_manifest (
  cell_table_manifest_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sample_id uuid NOT NULL REFERENCES core.sample(sample_id) ON DELETE CASCADE,
  quantification_run_id uuid REFERENCES spatial.quantification_run(quantification_run_id) ON DELETE SET NULL,
  file_id uuid NOT NULL REFERENCES files.file_object(file_id) ON DELETE CASCADE,
  table_format text NOT NULL,
  row_count bigint,
  cell_id_column text,
  x_column text,
  y_column text,
  cell_type_column text,
  marker_columns jsonb NOT NULL DEFAULT '[]',
  morphology_columns jsonb NOT NULL DEFAULT '[]',
  coordinate_system text,
  schema_json jsonb NOT NULL DEFAULT '{}',
  qc_status text DEFAULT 'unknown',
  created_at timestamptz NOT NULL DEFAULT now()
);
