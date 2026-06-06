# Ingestion Runbook

## Step 1: Apply database migration

```bash
psql "$DATABASE_URL" -f 03_DATABASE_MIGRATIONS.sql
```

## Step 2: Configure environment

Copy `06_CONFIG_ASSETS/env.example` into your backend environment and adjust values.

## Step 3: Create Qdrant collection

The backend should create `research_knowledge` with named vector `text` automatically. Verify with `/api/research-knowledge/status`.

## Step 4: Crawl public lab website

Call:

```bash
curl -X POST "$API_URL/api/research-knowledge/crawl/farkkila?max_pages=50"   -H "Authorization: Bearer $TOKEN"
```

## Step 5: Discover publications

```bash
curl -X POST "$API_URL/api/research-knowledge/ingest-publications"   -H "Authorization: Bearer $TOKEN"
```

## Step 6: Seed datasets

Load `07_TEMPLATES/dataset_registry_template.csv` or implement the dataset fetcher.

## Step 7: Run evaluation

Use `08_EVALUATION_AND_QA/retrieval_test_questions.md`.

## Step 8: Connect to AI assistant

Update `/ask` to use research knowledge search results as one retrieval leg.
