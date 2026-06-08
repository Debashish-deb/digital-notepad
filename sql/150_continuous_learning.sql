-- Teacher-Student Continuous Learning System
-- Migration: AI responses, claims, evidence, knowledge items, graph edges, user feedback

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS platform;

-- Storage status for knowledge items
-- VERIFIED | DRAFT | LOW_CONFIDENCE | REJECTED | DEPRECATED

CREATE TABLE IF NOT EXISTS platform.ai_responses (
    response_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id text,
    user_email text,
    query_text text NOT NULL,
    answer_text text NOT NULL,
    model_provider text,
    model_name text,
    model_role text NOT NULL DEFAULT 'student',
    intent text,
    project_codes text[] DEFAULT ARRAY[]::text[],
    source_ids jsonb DEFAULT '[]'::jsonb,
    citation_count integer NOT NULL DEFAULT 0,
    has_citations boolean NOT NULL DEFAULT false,
    pipeline_status text NOT NULL DEFAULT 'pending',
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ai_responses_model_role_chk CHECK (model_role IN ('teacher', 'student', 'expert')),
    CONSTRAINT ai_responses_pipeline_status_chk CHECK (
        pipeline_status IN ('pending', 'processing', 'completed', 'failed', 'skipped')
    )
);

CREATE INDEX IF NOT EXISTS idx_ai_responses_session ON platform.ai_responses (session_id) WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ai_responses_user ON platform.ai_responses (user_email) WHERE user_email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ai_responses_created ON platform.ai_responses (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_responses_pipeline ON platform.ai_responses (pipeline_status);

CREATE TABLE IF NOT EXISTS platform.extracted_claims (
    claim_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id uuid NOT NULL REFERENCES platform.ai_responses(response_id) ON DELETE CASCADE,
    claim_text text NOT NULL,
    claim_type text NOT NULL DEFAULT 'factual',
    confidence_score numeric NOT NULL DEFAULT 0.0,
    has_citation boolean NOT NULL DEFAULT false,
    extraction_method text NOT NULL DEFAULT 'rule_based',
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT extracted_claims_type_chk CHECK (
        claim_type IN ('factual', 'method', 'interpretation', 'hypothesis', 'note')
    )
);

CREATE INDEX IF NOT EXISTS idx_extracted_claims_response ON platform.extracted_claims (response_id);
CREATE INDEX IF NOT EXISTS idx_extracted_claims_confidence ON platform.extracted_claims (confidence_score DESC);

CREATE TABLE IF NOT EXISTS platform.evidence_sources (
    evidence_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id uuid REFERENCES platform.ai_responses(response_id) ON DELETE CASCADE,
    claim_id uuid REFERENCES platform.extracted_claims(claim_id) ON DELETE SET NULL,
    source_type text NOT NULL DEFAULT 'citation',
    title text,
    url text,
    doi text,
    pmid text,
    accession text,
    chunk_id text,
    source_uuid text,
    excerpt text,
    confidence_score numeric DEFAULT 0.0,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evidence_sources_response ON platform.evidence_sources (response_id);
CREATE INDEX IF NOT EXISTS idx_evidence_sources_claim ON platform.evidence_sources (claim_id) WHERE claim_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_evidence_sources_doi ON platform.evidence_sources (doi) WHERE doi IS NOT NULL;

CREATE TABLE IF NOT EXISTS platform.knowledge_items (
    knowledge_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id uuid REFERENCES platform.ai_responses(response_id) ON DELETE SET NULL,
    claim_id uuid REFERENCES platform.extracted_claims(claim_id) ON DELETE SET NULL,
    title text NOT NULL,
    content text NOT NULL,
    storage_status text NOT NULL DEFAULT 'DRAFT',
    confidence_score numeric NOT NULL DEFAULT 0.0,
    has_citation boolean NOT NULL DEFAULT false,
    entity_type text,
    classification text,
    version integer NOT NULL DEFAULT 1,
    supersedes_id uuid REFERENCES platform.knowledge_items(knowledge_id) ON DELETE SET NULL,
    contradiction_flags jsonb DEFAULT '[]'::jsonb,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deprecated_at timestamptz,
    CONSTRAINT knowledge_items_status_chk CHECK (
        storage_status IN ('VERIFIED', 'DRAFT', 'LOW_CONFIDENCE', 'REJECTED', 'DEPRECATED')
    ),
    CONSTRAINT knowledge_items_entity_type_chk CHECK (
        entity_type IS NULL OR entity_type IN (
            'cancer_type', 'marker', 'gene', 'protein', 'cell_type', 'pathway',
            'drug', 'therapy', 'patient_cohort', 'dataset', 'experiment',
            'publication', 'research_project', 'method', 'outcome'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_knowledge_items_status ON platform.knowledge_items (storage_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_confidence ON platform.knowledge_items (confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_response ON platform.knowledge_items (response_id) WHERE response_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_knowledge_items_title_trgm ON platform.knowledge_items USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_content_trgm ON platform.knowledge_items USING gin (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_supersedes ON platform.knowledge_items (supersedes_id) WHERE supersedes_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS platform.knowledge_graph_edges (
    edge_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_id uuid REFERENCES platform.knowledge_items(knowledge_id) ON DELETE CASCADE,
    subject_name text NOT NULL,
    subject_type text NOT NULL,
    relation_type text NOT NULL,
    object_name text NOT NULL,
    object_type text NOT NULL,
    confidence_score numeric NOT NULL DEFAULT 0.0,
    evidence_text text,
    storage_status text NOT NULL DEFAULT 'DRAFT',
    version integer NOT NULL DEFAULT 1,
    supersedes_edge_id uuid REFERENCES platform.knowledge_graph_edges(edge_id) ON DELETE SET NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deprecated_at timestamptz,
    CONSTRAINT knowledge_graph_edges_status_chk CHECK (
        storage_status IN ('VERIFIED', 'DRAFT', 'LOW_CONFIDENCE', 'REJECTED', 'DEPRECATED')
    ),
    CONSTRAINT knowledge_graph_edges_subject_type_chk CHECK (
        subject_type IN (
            'cancer_type', 'marker', 'gene', 'protein', 'cell_type', 'pathway',
            'drug', 'therapy', 'patient_cohort', 'dataset', 'experiment',
            'publication', 'research_project', 'method', 'outcome'
        )
    ),
    CONSTRAINT knowledge_graph_edges_object_type_chk CHECK (
        object_type IN (
            'cancer_type', 'marker', 'gene', 'protein', 'cell_type', 'pathway',
            'drug', 'therapy', 'patient_cohort', 'dataset', 'experiment',
            'publication', 'research_project', 'method', 'outcome'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_knowledge ON platform.knowledge_graph_edges (knowledge_id) WHERE knowledge_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kg_edges_subject ON platform.knowledge_graph_edges (subject_name, subject_type);
CREATE INDEX IF NOT EXISTS idx_kg_edges_object ON platform.knowledge_graph_edges (object_name, object_type);
CREATE INDEX IF NOT EXISTS idx_kg_edges_relation ON platform.knowledge_graph_edges (relation_type);
CREATE INDEX IF NOT EXISTS idx_kg_edges_status ON platform.knowledge_graph_edges (storage_status);

CREATE TABLE IF NOT EXISTS platform.user_feedback (
    feedback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id uuid REFERENCES platform.ai_responses(response_id) ON DELETE CASCADE,
    knowledge_id uuid REFERENCES platform.knowledge_items(knowledge_id) ON DELETE SET NULL,
    user_email text NOT NULL,
    feedback_type text NOT NULL,
    rating integer,
    comment text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT user_feedback_type_chk CHECK (
        feedback_type IN (
            'thumbs_up', 'thumbs_down', 'mark_useful', 'mark_incorrect',
            'needs_review', 'save_to_knowledge_base'
        )
    ),
    CONSTRAINT user_feedback_rating_chk CHECK (rating IS NULL OR rating BETWEEN -1 AND 1)
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_response ON platform.user_feedback (response_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_user ON platform.user_feedback (user_email);
CREATE INDEX IF NOT EXISTS idx_user_feedback_type ON platform.user_feedback (feedback_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_feedback_unique_per_type
    ON platform.user_feedback (response_id, user_email, feedback_type)
    WHERE response_id IS NOT NULL;
