-- Create platform schema
CREATE SCHEMA IF NOT EXISTS platform;

-- Researchers/Users table
CREATE TABLE IF NOT EXISTS platform.researcher (
  researcher_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username text NOT NULL UNIQUE,
  full_name text,
  role text NOT NULL DEFAULT 'researcher',
  allowed_project_codes text[] NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Register default developer user
INSERT INTO platform.researcher (username, full_name, role, allowed_project_codes)
VALUES ('debdeba', 'Lead Bioinformatician', 'admin', '{"SPACE", "EyeMT", "KRAS"}')
ON CONFLICT (username) DO NOTHING;

-- Software Tools registry
CREATE TABLE IF NOT EXISTS platform.software_tool (
  tool_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_name text NOT NULL UNIQUE,
  current_version text,
  description text
);

-- Populate default software tools
INSERT INTO platform.software_tool (tool_name, current_version, description) VALUES
('napari', '0.4.19', 'Multi-dimensional image viewer for Python'),
('cylinter', '0.1.5', 'Quality control pipeline for multiplex microscopy images'),
('ashlar', '1.17.0', 'Algorithms for Stitching and Registration of Microscopic Images'),
('basic', '1.0.3', 'Background and Shading Illumination Correction for microscopy'),
('mesmer', '0.12.3', 'DeepCell deep-learning cell segmentation model'),
('stardist', '0.8.5', 'Object Detection with Star-convex Shapes for 2D and 3D nuclei segmentation'),
('python_env', '3.10.x', 'Standardized scientific Python programming environment'),
('cuda_gpu', '12.2', 'NVIDIA CUDA toolkit and GPU driver libraries'),
('docker', '24.x', 'Containerization engine for local pipeline running'),
('apptainer', '1.2.x', 'High Performance Computing container runtime (formerly Singularity)')
ON CONFLICT (tool_name) DO NOTHING;

-- Installation Recipes table
CREATE TABLE IF NOT EXISTS platform.installation_recipe (
  recipe_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_id uuid REFERENCES platform.software_tool(tool_id) ON DELETE CASCADE,
  os_platform text NOT NULL, -- 'windows', 'macos', 'linux'
  architecture text NOT NULL DEFAULT 'x86_64', -- 'x86_64', 'arm64' (Apple Silicon)
  recommended_method text NOT NULL, -- 'conda', 'pip', 'apt', 'docker', 'manual'
  commands text NOT NULL,
  expected_output text,
  verification_command text,
  common_errors jsonb NOT NULL DEFAULT '[]',
  uninstall_commands text
);

-- HPC Slurm templates table
CREATE TABLE IF NOT EXISTS platform.hpc_template (
  template_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_name text NOT NULL UNIQUE,
  target_hpc text NOT NULL, -- 'lumi', 'generic_slurm'
  template_body text NOT NULL,
  description text
);

-- Conversations table
CREATE TABLE IF NOT EXISTS platform.conversation (
  conversation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  researcher_id uuid REFERENCES platform.researcher(researcher_id) ON DELETE CASCADE,
  title text,
  project_code text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Chat messages table
CREATE TABLE IF NOT EXISTS platform.message (
  message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid REFERENCES platform.conversation(conversation_id) ON DELETE CASCADE,
  role text NOT NULL, -- 'user', 'assistant'
  content text NOT NULL,
  retrieved_chunks jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Generated scripts audit logging
CREATE TABLE IF NOT EXISTS platform.generated_script (
  script_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid REFERENCES platform.conversation(conversation_id) ON DELETE SET NULL,
  script_name text,
  script_body text NOT NULL,
  target_language text NOT NULL, -- 'bash', 'powershell', 'python', 'r', 'yaml'
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Script validation results
CREATE TABLE IF NOT EXISTS platform.validation_result (
  validation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  script_id uuid REFERENCES platform.generated_script(script_id) ON DELETE CASCADE,
  status text NOT NULL, -- 'passed', 'failed', 'warnings'
  output_log text,
  created_at timestamptz NOT NULL DEFAULT now()
);
