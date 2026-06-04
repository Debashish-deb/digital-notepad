-- Create tables for AI Model Registry, Infrastructure Registry, Document Ingestion, Publications, and Checklists

CREATE TABLE IF NOT EXISTS platform.ai_model (
  model_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  model_type text NOT NULL, -- 'LLM', 'biomedical_LLM', 'embedding', 'vision', 'segmentation', 'spatial_biology'
  source text,
  license text,
  parameters text,
  gpu_requirements text,
  memory_requirements text,
  local_deployment boolean NOT NULL DEFAULT true,
  api_deployment boolean NOT NULL DEFAULT false,
  use_cases text,
  strengths text,
  weaknesses text,
  installation_instructions text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.infrastructure (
  resource_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  resource_type text NOT NULL, -- 'workstation', 'server', 'lumi', 'csc', 'storage', 'database'
  operating_system text,
  cpu_specs text,
  ram_specs text,
  gpu_specs text,
  storage_specs text,
  installed_software text[] NOT NULL DEFAULT '{}',
  access_notes text,
  maintenance_notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.document_ingestion (
  doc_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  file_type text NOT NULL, -- 'pdf', 'docx', 'txt', 'md', 'html', 'ipynb', 'r_script', 'py_script', 'yaml', 'json', 'csv'
  extracted_text text,
  tags text[] NOT NULL DEFAULT '{}',
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  software_associations text[] NOT NULL DEFAULT '{}',
  pipeline_stage_associations text[] NOT NULL DEFAULT '{}',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.publication (
  pub_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  authors text NOT NULL,
  journal text NOT NULL,
  publication_year integer NOT NULL,
  doi text UNIQUE,
  pmid text UNIQUE,
  abstract text,
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  full_text_path text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.onboarding_checklist (
  checklist_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES core.project(project_id) ON DELETE CASCADE,
  category text NOT NULL, -- 'project', 'document', 'software', 'pipeline', 'hpc', 'model', 'dataset', 'sample', 'publication'
  item_name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'pending', -- 'pending', 'completed', 'not_applicable'
  checked_by_id uuid REFERENCES platform.researcher(researcher_id) ON DELETE SET NULL,
  checked_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT unique_project_category_item UNIQUE (project_id, category, item_name)
);
