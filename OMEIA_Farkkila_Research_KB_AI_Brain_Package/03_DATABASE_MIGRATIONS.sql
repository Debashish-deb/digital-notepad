-- OMEIA / Färkkilä Lab Research Knowledge Base
-- Migration: public/internal research source registry, knowledge graph, chunks, evaluation
-- Review with your DB admin before applying to production.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS platform;

CREATE TABLE IF NOT EXISTS platform.research_source (
    source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type text NOT NULL,
    title text NOT NULL,
    url text,
    canonical_url text,
    doi text,
    pmid text,
    dataset_accession text,
    publisher text,
    journal text,
    publication_year integer,
    authors jsonb DEFAULT '[]'::jsonb,
    abstract text,
    license text,
    access_level text NOT NULL DEFAULT 'public',
    fetched_at timestamptz,
    last_checked_at timestamptz,
    checksum text,
    status text NOT NULL DEFAULT 'discovered',
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT research_source_access_level_chk CHECK (access_level IN ('public', 'internal', 'restricted')),
    CONSTRAINT research_source_status_chk CHECK (status IN ('discovered', 'fetched', 'parsed', 'chunked', 'indexed', 'evaluated', 'failed'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_research_source_canonical_url ON platform.research_source (canonical_url) WHERE canonical_url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_research_source_type ON platform.research_source (source_type);
CREATE INDEX IF NOT EXISTS idx_research_source_doi ON platform.research_source (doi) WHERE doi IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_research_source_pmid ON platform.research_source (pmid) WHERE pmid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_research_source_dataset ON platform.research_source (dataset_accession) WHERE dataset_accession IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_research_source_status ON platform.research_source (status);

CREATE TABLE IF NOT EXISTS platform.research_document (
    document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid REFERENCES platform.research_source(source_id) ON DELETE CASCADE,
    title text NOT NULL,
    document_type text NOT NULL DEFAULT 'unknown',
    raw_text text,
    clean_text text,
    summary text,
    key_findings jsonb DEFAULT '[]'::jsonb,
    methods jsonb DEFAULT '{}'::jsonb,
    limitations jsonb DEFAULT '[]'::jsonb,
    data_availability text,
    citation_text text,
    visibility text NOT NULL DEFAULT 'public',
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT research_document_visibility_chk CHECK (visibility IN ('public', 'internal', 'restricted'))
);

CREATE INDEX IF NOT EXISTS idx_research_document_source ON platform.research_document (source_id);
CREATE INDEX IF NOT EXISTS idx_research_document_type ON platform.research_document (document_type);
CREATE INDEX IF NOT EXISTS idx_research_document_visibility ON platform.research_document (visibility);

CREATE TABLE IF NOT EXISTS platform.research_chunk (
    chunk_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid REFERENCES platform.research_document(document_id) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    text text NOT NULL,
    text_hash text NOT NULL,
    token_count integer,
    section_title text,
    qdrant_collection text,
    qdrant_point_id text,
    vector_status text NOT NULL DEFAULT 'pending',
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index),
    CONSTRAINT research_chunk_vector_status_chk CHECK (vector_status IN ('pending', 'indexed', 'failed', 'skipped'))
);

CREATE INDEX IF NOT EXISTS idx_research_chunk_document ON platform.research_chunk (document_id);
CREATE INDEX IF NOT EXISTS idx_research_chunk_hash ON platform.research_chunk (text_hash);
CREATE INDEX IF NOT EXISTS idx_research_chunk_vector_status ON platform.research_chunk (vector_status);

CREATE TABLE IF NOT EXISTS platform.research_dataset (
    dataset_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    accession text,
    source_database text NOT NULL,
    title text NOT NULL,
    disease text,
    modality text[] DEFAULT ARRAY[]::text[],
    organism text DEFAULT 'Homo sapiens',
    sample_count text,
    patient_count text,
    technology text[] DEFAULT ARRAY[]::text[],
    url text,
    related_source_id uuid REFERENCES platform.research_source(source_id) ON DELETE SET NULL,
    access_level text NOT NULL DEFAULT 'public',
    license text,
    usable_for text[] DEFAULT ARRAY[]::text[],
    limitations text[] DEFAULT ARRAY[]::text[],
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT research_dataset_access_level_chk CHECK (access_level IN ('public', 'internal', 'restricted'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_research_dataset_accession ON platform.research_dataset (source_database, accession) WHERE accession IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_research_dataset_modality ON platform.research_dataset USING GIN (modality);
CREATE INDEX IF NOT EXISTS idx_research_dataset_technology ON platform.research_dataset USING GIN (technology);

CREATE TABLE IF NOT EXISTS platform.knowledge_entity (
    entity_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    normalized_name text NOT NULL,
    entity_type text NOT NULL,
    aliases text[] DEFAULT ARRAY[]::text[],
    description text,
    source_ids uuid[] DEFAULT ARRAY[]::uuid[],
    confidence numeric DEFAULT 0.0,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_entity_norm_type ON platform.knowledge_entity (normalized_name, entity_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_entity_aliases ON platform.knowledge_entity USING GIN (aliases);
CREATE INDEX IF NOT EXISTS idx_knowledge_entity_type ON platform.knowledge_entity (entity_type);

CREATE TABLE IF NOT EXISTS platform.knowledge_relation (
    relation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_entity_id uuid REFERENCES platform.knowledge_entity(entity_id) ON DELETE CASCADE,
    relation_type text NOT NULL,
    object_entity_id uuid REFERENCES platform.knowledge_entity(entity_id) ON DELETE CASCADE,
    evidence_text text,
    source_id uuid REFERENCES platform.research_source(source_id) ON DELETE SET NULL,
    confidence numeric DEFAULT 0.0,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_relation_subject ON platform.knowledge_relation (subject_entity_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_relation_object ON platform.knowledge_relation (object_entity_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_relation_type ON platform.knowledge_relation (relation_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_relation_source ON platform.knowledge_relation (source_id);

CREATE TABLE IF NOT EXISTS platform.research_ingestion_job (
    job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type text NOT NULL,
    source_url text,
    status text NOT NULL DEFAULT 'queued',
    started_at timestamptz,
    finished_at timestamptz,
    records_discovered integer DEFAULT 0,
    records_fetched integer DEFAULT 0,
    records_indexed integer DEFAULT 0,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_by_email text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT research_ingestion_job_status_chk CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_research_ingestion_job_status ON platform.research_ingestion_job (status);
CREATE INDEX IF NOT EXISTS idx_research_ingestion_job_type ON platform.research_ingestion_job (job_type);

CREATE TABLE IF NOT EXISTS platform.research_query_eval (
    eval_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    query text NOT NULL,
    category text,
    expected_sources text[] DEFAULT ARRAY[]::text[],
    expected_entities text[] DEFAULT ARRAY[]::text[],
    expected_answer_points text[] DEFAULT ARRAY[]::text[],
    answer text,
    retrieved_source_ids text[] DEFAULT ARRAY[]::text[],
    score numeric,
    failure_reason text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_research_query_eval_category ON platform.research_query_eval (category);
CREATE INDEX IF NOT EXISTS idx_research_query_eval_score ON platform.research_query_eval (score);

-- Optional text search indexes. Adjust language/config as needed.
CREATE INDEX IF NOT EXISTS idx_research_source_title_trgm ON platform.research_source USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_research_document_title_trgm ON platform.research_document USING gin (title gin_trgm_ops);
