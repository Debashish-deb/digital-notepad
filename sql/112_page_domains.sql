-- Page domain registry (LUMI-W001) — IA lens, not storage root.

CREATE TABLE IF NOT EXISTS platform.page_domain (
  page_domain_id text PRIMARY KEY,
  label text NOT NULL,
  sort_order integer NOT NULL DEFAULT 0,
  description text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.page_section (
  page_section_id text PRIMARY KEY,
  page_domain_id text NOT NULL REFERENCES platform.page_domain(page_domain_id) ON DELETE CASCADE,
  label text NOT NULL,
  nav_screen text,
  database_section_id text,
  sort_order integer NOT NULL DEFAULT 0,
  description text,
  created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO platform.page_domain (page_domain_id, label, sort_order, description) VALUES
  ('dashboard', 'Dashboard', 10, 'Lab status and shortcuts'),
  ('overview', 'Overview / Lab Operations', 20, 'General lab information and operations'),
  ('research_hub', 'Research Hub', 30, 'Research themes and dissemination'),
  ('projects', 'Projects', 40, 'Project portfolio and digital twins'),
  ('data_storage', 'Data & Storage', 50, 'Vault, connectors, storage health'),
  ('computational', 'Computational Hub', 60, 'HPC, tools, environments'),
  ('cycif', 'CyCIF / Image Analysis', 70, 'Imaging pipeline and QC'),
  ('wet_lab', 'Wet Lab', 80, 'Protocols, reagents, wet-lab files'),
  ('orders', 'Orders & Procurement', 90, 'Billing and procurement archive'),
  ('social', 'Social & Miscellaneous', 100, 'Lab social memory'),
  ('knowledge_base', 'Knowledge Base', 110, 'Search, review queue, uncategorized'),
  ('notebook', 'Notebook / Wiki', 120, 'Notebook and wiki entries'),
  ('tasks_decisions', 'Tasks & Decisions', 130, 'Tasks and decision register'),
  ('ai_assistant', 'AI Lab Assistant', 140, 'Copilot and tooling (deprioritized)'),
  ('administration', 'Administration', 150, 'Users, jobs, security')
ON CONFLICT (page_domain_id) DO NOTHING;

INSERT INTO platform.page_section (page_section_id, page_domain_id, label, nav_screen, database_section_id, sort_order) VALUES
  ('dashboard.main', 'dashboard', 'Lab dashboard', 'dashboard', NULL, 1),
  ('overview.get_started', 'overview', 'General lab information', 'lab_knowledge', NULL, 1),
  ('overview.onboarding', 'overview', 'Onboarding & Outboarding', 'lab_knowledge', 'overview_onboarding', 2),
  ('overview.guidelines', 'overview', 'Guidelines', 'lab_knowledge', 'overview_guidelines', 3),
  ('overview.documents', 'overview', 'Documents & Permits', 'lab_knowledge', 'overview_documents', 4),
  ('overview.personnel', 'overview', 'Personnel', 'lab_knowledge', 'overview_personnel', 5),
  ('overview.cleaning', 'overview', 'Cleaning / Maintenance', 'lab_knowledge', 'overview_cleaning', 6),
  ('research.materials', 'research_hub', 'Research materials', 'lab_knowledge', 'overview_research_materials', 1),
  ('projects.portfolio', 'projects', 'Project portfolio', 'projects', NULL, 1),
  ('projects.twin', 'projects', 'Project digital twin', 'projects', NULL, 2),
  ('projects.files', 'projects', 'Project files', 'projects', NULL, 3),
  ('data.roots', 'data_storage', 'Storage roots', 'data_storage', NULL, 1),
  ('data.vault', 'data_storage', 'Raw knowledge vault', 'data_storage', NULL, 2),
  ('data.registry', 'data_storage', 'File registry', 'data_storage', NULL, 3),
  ('computational.hub', 'computational', 'Computational Hub', 'bioinformatics', NULL, 1),
  ('cycif.pipeline', 'cycif', 'Imaging pipeline', 'cycif_pipeline', NULL, 1),
  ('cycif.install', 'cycif', 'Tool setup', 'cycif_install', NULL, 2),
  ('wet.files', 'wet_lab', 'Lab database files', 'lab_knowledge', 'wet_lab_files', 1),
  ('wet.protocols', 'wet_lab', 'Wet-lab protocols', 'wet_protocols', NULL, 2),
  ('orders.billing', 'orders', 'Billing & ordering', 'lab_knowledge', 'orders_billing', 1),
  ('orders.archive', 'orders', 'Archive', 'lab_knowledge', 'orders_archive', 2),
  ('social.browse', 'social', 'Browse', 'lab_knowledge', 'social_misc', 1),
  ('knowledge.search', 'knowledge_base', 'Semantic search', 'lab_knowledge', NULL, 1),
  ('knowledge.review', 'knowledge_base', 'Review queue', 'data_storage', NULL, 2),
  ('notebook.wiki', 'notebook', 'Living notebook', 'notebook', NULL, 1),
  ('tasks.main', 'tasks_decisions', 'Task planner', 'tasks', NULL, 1),
  ('decisions.main', 'tasks_decisions', 'Research decisions', 'decisions', NULL, 2),
  ('ai.copilot', 'ai_assistant', 'Chat copilot', 'chat', NULL, 1),
  ('admin.users', 'administration', 'Users & allowlist', 'administration', NULL, 1),
  ('admin.jobs', 'administration', 'Ingestion jobs', 'administration', NULL, 2)
ON CONFLICT (page_section_id) DO NOTHING;
