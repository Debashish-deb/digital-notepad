# Acceptance Criteria

The implementation is acceptable when:

1. The assistant can answer lab identity and research-domain questions with citations.
2. The assistant can retrieve Färkkilä Lab publications from indexed metadata.
3. The assistant can retrieve dataset records such as GSE211956.
4. The assistant can explain MHC class II / HGSC context using indexed sources.
5. The assistant can explain TLS ovarian cancer context using indexed sources.
6. Every answer with scientific claims includes citations.
7. Qdrant indexing is real and verifiable.
8. PostgreSQL registry tables track source/document/chunk/dataset state.
9. Internal and restricted sources are not exposed to unauthorized users.
10. No patient-identifiable text is sent to public LLMs.
11. A regression/evaluation suite exists and can be re-run after ingestion.
12. The frontend has an admin/search UI for source status and retrieval tests.

Do not claim production readiness until all criteria are checked.
