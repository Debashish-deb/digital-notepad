# 10 — Complete Setup Step by Step

## 1. Unpack

```bash
unzip farkki_ai_platform_blueprint.zip
cd farkki_ai_platform_blueprint
```

## 2. Start local services

```bash
docker compose -f configs/docker-compose.dev.yml up -d
```

Expected:

```text
PostgreSQL  localhost:5432
Qdrant      localhost:6333
Neo4j       localhost:7474 and bolt://localhost:7687
MinIO       localhost:9000 and console localhost:9001
```

## 3. Create Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app_skeleton/api/requirements.txt
```

## 4. Create vector collections

```bash
export QDRANT_URL=http://localhost:6333
python scripts/create_qdrant_collections.py
```

## 5. Validate manifest templates

```bash
python scripts/validate_manifests.py
```

## 6. Generate synthetic data

```bash
python scripts/synthetic_seed_data.py
```

## 7. Ingest demo docs

```bash
python scripts/ingest_documents_demo.py
python scripts/query_copilot_demo.py
```

## 8. Start API

```bash
uvicorn app_skeleton.api.main:app --reload --host 0.0.0.0 --port 8000
```

Test:

```text
http://localhost:8000/health
```

## 9. Start UI

```bash
pip install streamlit
streamlit run app_skeleton/ui/streamlit_app.py
```

## 10. Add your real documentation, not patient data

1. Put docs/scripts in a safe folder.
2. Add rows to `schemas/document_manifest_template.csv`.
3. Set sensitivity.
4. Parse and chunk.
5. Embed.
6. Test retrieval.
7. Approve.

## 11. Onboard first project

Fill:

```text
schemas/project_registry_template.csv
schemas/data_inventory_template.csv
schemas/clinical_dictionary_template.csv
schemas/assay_registry_template.csv
schemas/document_manifest_template.csv
schemas/pipeline_run_manifest_template.csv
```

## 12. Before real patient data

Do not proceed until:

- direct identifiers are excluded
- access policy exists
- audit logging works
- external LLM policy is clear
- backups are tested
- synthetic end-to-end test passes
