# OMEIA / Färkkilä Lab Research Knowledge Base + AI Brain Package

Created: 2026-06-06

This folder is a complete handoff package for a coding AI. It contains the prompt, architecture, database schema, backend/frontend scaffolds, seed-source assets, evaluation questions, privacy rules, and runbooks needed to build a professional research knowledge base for the OMEIA / Färkkilä Lab Assistant.

## What this package is for

The goal is to teach the lab assistant the research domain in a source-grounded way, not by blindly fine-tuning a model. The recommended system is:

```txt
Unified Search + RAG + Knowledge Graph + Evaluation + Scheduled Refresh
```

This lets the assistant answer with source links, publications, datasets, internal protocols, confidence, and uncertainty when evidence is missing.

## Give these files to your coding AI in this order

1. `COPY_THIS_MASTER_PROMPT_TO_AI.md`
2. `00_EXECUTIVE_CONTEXT.md`
3. `01_ARCHITECTURE_BLUEPRINT.md`
4. `02_SOURCE_SEEDS_AND_RESEARCH_MAP.md`
5. `03_DATABASE_MIGRATIONS.sql`
6. `04_BACKEND_SCAFFOLDING/`
7. `05_FRONTEND_SCAFFOLDING/`
8. `06_CONFIG_ASSETS/`
9. `08_EVALUATION_AND_QA/`
10. `09_RUNBOOKS/`

## Key principle

Do **not** build another isolated chatbot. Build a living research knowledge infrastructure where every answer can trace back to a source.

## Accuracy goal

Do not promise 100% or 98% accuracy until evaluation proves it. The realistic goal is:

- 95–98% source-grounded correctness for covered/indexed topics
- 100% citation requirement for scientific claims
- safe refusal or qualification for uncovered topics

## Main output expected from coding AI

- database migration
- crawler/fetcher/indexer services
- Qdrant `research_knowledge` collection
- PostgreSQL registry tables
- research admin UI
- unified search integration
- AI assistant RAG integration
- evaluation suite
- run/test results
