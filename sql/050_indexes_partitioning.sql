CREATE INDEX IF NOT EXISTS idx_project_code ON core.project(project_code);
CREATE INDEX IF NOT EXISTS idx_sample_code ON core.sample(sample_code);
CREATE INDEX IF NOT EXISTS idx_sample_project ON core.sample(project_id);
CREATE INDEX IF NOT EXISTS idx_patient_code ON core.patient(patient_code);
CREATE INDEX IF NOT EXISTS idx_marker_canonical_trgm ON core.marker USING gin (canonical_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_file_project ON files.file_object(project_id);
CREATE INDEX IF NOT EXISTS idx_file_sample ON files.file_object(sample_id);
CREATE INDEX IF NOT EXISTS idx_file_sha256 ON files.file_object(sha256);
CREATE INDEX IF NOT EXISTS idx_file_role ON files.file_object(file_role);
CREATE INDEX IF NOT EXISTS idx_file_metadata_gin ON files.file_object USING gin(metadata);

CREATE INDEX IF NOT EXISTS idx_clinical_hrd ON clinical.patient_clinical_summary(hrd_status);
CREATE INDEX IF NOT EXISTS idx_clinical_brca ON clinical.patient_clinical_summary(brca_status);
CREATE INDEX IF NOT EXISTS idx_clinical_platinum ON clinical.patient_clinical_summary(platinum_response);

CREATE INDEX IF NOT EXISTS idx_assay_run_project ON assay.assay_run(project_id);
CREATE INDEX IF NOT EXISTS idx_assay_run_type ON assay.assay_run(assay_type);
CREATE INDEX IF NOT EXISTS idx_segmentation_sample ON spatial.segmentation_run(sample_id);
CREATE INDEX IF NOT EXISTS idx_quantification_sample ON spatial.quantification_run(sample_id);

CREATE INDEX IF NOT EXISTS idx_feature_definition_name ON features.feature_definition(feature_name);
CREATE INDEX IF NOT EXISTS idx_feature_definition_group ON features.feature_definition(feature_group);
CREATE INDEX IF NOT EXISTS idx_feature_value_feature ON features.feature_value(feature_id);
CREATE INDEX IF NOT EXISTS idx_feature_value_entity_code ON features.feature_value(entity_type, entity_code);

CREATE INDEX IF NOT EXISTS idx_document_source_project ON rag.document_source(project_id);
CREATE INDEX IF NOT EXISTS idx_document_source_type ON rag.document_source(source_type);
CREATE INDEX IF NOT EXISTS idx_document_chunk_text_trgm ON rag.document_chunk USING gin (chunk_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_vector_registry_collection ON rag.vector_point_registry(collection_name);
CREATE INDEX IF NOT EXISTS idx_vector_registry_project ON rag.vector_point_registry(project_id);
CREATE INDEX IF NOT EXISTS idx_vector_payload_gin ON rag.vector_point_registry USING gin(payload);

CREATE INDEX IF NOT EXISTS idx_audit_event_time ON audit.event_log(event_time);
CREATE INDEX IF NOT EXISTS idx_audit_event_user ON audit.event_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_event_project ON audit.event_log(project_id);

-- For production, partition large tables such as audit.event_log and optional cell-level tables by month/project/sample.
