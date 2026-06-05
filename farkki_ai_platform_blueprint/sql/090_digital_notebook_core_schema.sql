-- Create digital notebook schema extensions for version history, decisions, and wikis

CREATE TABLE IF NOT EXISTS platform.notebook_revision (
  revision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_id uuid NOT NULL REFERENCES platform.notebook_entry(entry_id) ON DELETE CASCADE,
  revision_number integer NOT NULL,
  title text NOT NULL,
  content text NOT NULL,
  conclusions text,
  issues_found text,
  decisions_made text,
  next_steps text,
  tags text[] NOT NULL DEFAULT '{}',
  author_id uuid REFERENCES platform.researcher(researcher_id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.decision_registry (
  decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.project(project_id) ON DELETE CASCADE,
  title text NOT NULL,
  decision_details text NOT NULL,
  rationale text NOT NULL,
  alternatives_considered text,
  decided_by_id uuid REFERENCES platform.researcher(researcher_id) ON DELETE SET NULL,
  decision_date date NOT NULL DEFAULT CURRENT_DATE,
  linked_notebook_entry_id uuid REFERENCES platform.notebook_entry(entry_id) ON DELETE SET NULL,
  linked_dataset_id uuid REFERENCES platform.dataset_catalog(dataset_id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.research_wiki (
  wiki_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  slug text NOT NULL UNIQUE,
  content text NOT NULL,
  wiki_type text NOT NULL DEFAULT 'SOP', -- 'SOP', 'protocol', 'software_guide', 'troubleshooting_guide'
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  created_by_id uuid REFERENCES platform.researcher(researcher_id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.wiki_revision (
  revision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  wiki_id uuid NOT NULL REFERENCES platform.research_wiki(wiki_id) ON DELETE CASCADE,
  revision_number integer NOT NULL,
  title text NOT NULL,
  content text NOT NULL,
  author_id uuid REFERENCES platform.researcher(researcher_id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
