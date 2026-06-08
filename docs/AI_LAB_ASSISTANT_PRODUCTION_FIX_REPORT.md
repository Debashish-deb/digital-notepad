# OMEIA AI Lab Assistant — Production Fix Report

**Date:** 2026-06-06  
**Branch:** `cursor/unified-search-ai-lab-assistant`  
**Baseline (pre-fix):** 29.8% overall pass, 86% intent, research bucket gate FAIL  
**After fix (mock eval):** 77.2% overall pass, 96.5% intent, research bucket gate PASS

## Verdict

**Not release-ready** for the ≥85% overall gold-set gate, but **major retrieval and intent regressions are fixed**. Mock-mode eval is now a reliable retrieval/citation gate; live Gemini eval was not re-run (API quota exhausted during session).

## Root causes fixed

| Issue | Root cause | Fix |
|-------|------------|-----|
| Research KB invisible in ⌘K | `SearchFilters` / `BUCKET_ORDER` omitted `research` | Added `research` (+ `people`) to frontend scopes and bucket labels |
| Research bucket gate fail | File hits dominated merged ranking; research appended after rerank window | Research-only fetch + sort + `_reserve_bucket_slots()` guarantees ≥2 research hits |
| Intent misclassification | Substring `"app"` in `"project"`, `"search"` in `"research"` | Word-boundary matching; reorder protocol/coding/research before app_help |
| Mock answers looked empty despite sources | `_extract_sources()` only parsed legacy prompt format | Parse grounded `[n] Title\nType:…\nExcerpt:` format |
| Dual RAG duplication | `RAGAgent.retrieve()` always merged | Legacy RAG only when `CHAT_USE_LEGACY_RAG=true` and unified hits sparse |
| People questions | No people index | `configs/lab_people_index.json` + `people_index.py` + `people` bucket |
| Weak ACL | `can_read_*` always True | Role/project/visibility checks with safe defaults |
| Research cards dead-end | No external URLs on cards | DOI/PubMed/profile links in `AssistantSearchHits.jsx` |

## Architecture (after)

```
ChatWidget → POST /api/chat → answer_chat()
  → classify_chat_intent() [word-boundary, protocol/research ordering]
  → SearchService.hits_for_copilot() [canonical retrieval]
      → unified_search (scopes by intent)
      → research/lab slot reservation
  → optional RAGAgent.retrieve() [CHAT_USE_LEGACY_RAG only]
  → llm_client (mock parses grounded prompts)
  → citation enforcement

GlobalSearchOverlay → GET /api/platform/unified-search
  → scopes include research, people (default: all)
```

## Files changed

**Backend:** `chat_intent.py`, `chat_service.py`, `search_service.py`, `search_models.py`, `search_nav.py`, `llm_client.py`, `people_index.py`, `permissions.py`  
**Frontend:** `SearchFilters.jsx`, `searchHits.js`, `AssistantSearchHits.jsx`  
**Config/data:** `configs/lab_people_index.json`  
**Docs:** this file

## Eval results (mock — `LLM_PROVIDER=mock`)

| Gate | Result | Target |
|------|--------|--------|
| Intent accuracy | **96.5%** ✓ | ≥95% |
| Citation compliance | **100%** ✓ | 100% |
| PII gate | **PASS** ✓ | pass |
| Research bucket gate | **PASS** ✓ | ≥70% |
| Provider honesty | **100%** ✓ | 100% |
| Overall gold pass | **77.2%** ✗ | ≥85% |

Report saved: `tests/search_qa_ai_last_run_mock.json`

### Remaining overall failures (mostly corpus / mock synthesis)

- **Key-term strictness:** e.g. `TLS` abbreviation, `spatial`/`HGSC` not always in mock excerpt bullets
- **Vault bucket:** some protocol questions expect vault hits not present in index
- **Finnish responses:** `response_lang=fi` items need live LLM or Finnish mock templates
- **Corpus gaps:** tCyCIF-in-lab-context expects both `research` + `lab` buckets; lab SOP corpus thin for some tools

## How to run locally

```bash
# Start stack
./start.sh

# Mock eval (deterministic retrieval gate)
LLM_PROVIDER=mock CHAT_LLM_PROVIDER=mock .venv/bin/python3 scripts/search/run_ai_lab_assistant_eval.py

# Live Gemini eval (server-side key only; watch rate limits)
LLM_PROVIDER=gemini CHAT_LLM_PROVIDER=gemini .venv/bin/python3 scripts/search/run_ai_lab_assistant_eval.py

# Unit tests
python3 -m unittest tests.test_chat_intent -v
cd apps/web && npm run build
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` / `CHAT_LLM_PROVIDER` | `mock` for CI; `gemini` for production synthesis |
| `GEMINI_API_KEY` | Server-side only (`configs/.env`) |
| `CHAT_USE_LEGACY_RAG` | `true` to enable fallback `RAGAgent.retrieve()` |
| `COPILOT_MIN_SIMILARITY` | Minimum hit score threshold (default 0.06) |
| `QDRANT_URL` | Research + doc chunk vectors (default `http://localhost:6333`) |

## Ingestion / expansion (next steps)

1. **Research KB:** `scripts/document-library/setup_research_knowledge.sh` — target more PubMed/GEO accessions from publications
2. **People:** edit `configs/lab_people_index.json` (sync from `teamDirectory.js` / `userProfilesData.js`)
3. **Datasets:** extend `dataset_fetcher.py` accession extraction from publication metadata
4. **Lab protocols:** ingest Ashlar/BaSiC/StarDist SOPs into lab Qdrant for protocol bucket gate

## Remaining risks

- Live Gemini quality unverified this session (free-tier quota exhausted)
- Notebook/wiki static JS vs Postgres drift not fully migrated (Phase 10 partial)
- Dataset count still low (~3 seeded + research metadata)
- Overall gate needs corpus enrichment or slightly relaxed key-term checks for mock mode

## Local Ollama research models (Färkkilä / OMEIA)

Docker service `omeia-ollama` stores weights in volume `omeia-ollama-data` (not host `~/.ollama`). On Mac thin client (`DOCKER_LOCAL=false`), run Docker on a Linux workstation and tunnel with `scripts/llm/ollama_ssh_tunnel.sh` — see `docs/DOCKER_SECURITY_AND_CONNECTION.md`.

| Tag | Tier | Specialty | OMEIA use |
|-----|------|-----------|-----------|
| `qwen2.5:3b` | fast | fast_eval | Default low-latency lab assistant |
| `llama3.2:3b-instruct` | fast | fast_eval | Alternate small instruct |
| `medgemma:4b` | medium | medical_general, cancer_oncology | MedGemma biomedical Q&A |
| `meditron:7b` | medium | medical_general, cancer_oncology | Clinical research (Meditron) |
| `medllama2:7b` | medium | medical_general, cancer_oncology | **Recommended for HGSC / oncology / immunotherapy** |
| `qwen2.5:7b-instruct` | medium | spatial_biology, synthesis | **Recommended for Visium / GeoMx / TME / TLS methods** |
| `llama3.1:8b-instruct` | medium | lab_assistant | General scientific summarization |
| `mistral-nemo:12b` | large | spatial_biology, synthesis | Long-form multi-source synthesis |

Catalog source: `configs/ollama_research_models.json`. Setup: `scripts/llm/setup_ollama_local_llm.sh` (logs: `logs/ollama_setup.log`, `logs/ollama_model_pulls.log`). BioMistral is not on the Ollama registry; use Meditron/MedLlama2 instead.

