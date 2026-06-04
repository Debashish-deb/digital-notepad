-- Canonical lab knowledge corpus (non-project operational docs).
-- Projects continue to use project workspace streaming; lab folders ingest here only.

CREATE INDEX IF NOT EXISTS idx_rag_document_source_corpus
  ON rag.document_source ((metadata->>'corpus'));

CREATE INDEX IF NOT EXISTS idx_rag_document_source_section
  ON rag.document_source ((metadata->>'section_id'));

CREATE INDEX IF NOT EXISTS idx_rag_document_chunk_text_trgm
  ON rag.document_chunk USING gin (chunk_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_rag_vector_point_corpus
  ON rag.vector_point_registry ((payload->>'corpus'));
