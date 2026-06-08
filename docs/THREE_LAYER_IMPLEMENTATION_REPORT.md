# Three-Layer AI Implementation Report

**Date:** June 2026  
**Branch:** `cursor/unified-search-ai-lab-assistant`

---

## Phase A — Layer 2 Conversation (complete)

### Changes
- Conversation-only fast path in `answer_chat()` — no RAG for smalltalk/general chat
- Enhanced `/api/chat/status` with `ollama_reachable`, `fallback_state`, `layers` flags
- Smalltalk patterns already extended (prior commit)

### Feature flags
- `LLM_PROVIDER=ollama`, `CHAT_LLM_PROVIDER=ollama`
- `CHAT_GREETING_MODEL`, `CHAT_CONVERSATION_MODEL`

### Linux deploy
```bash
cd ~/data4TB/digital-notepad && git pull
./infra/scripts/llm/ensure_linux_ollama.sh
docker exec omeia-ollama ollama pull qwen2.5:3b qwen2.5:7b-instruct
./scripts/start_linux.sh
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/chat/status | jq .
```

### Rollback
Set `LLM_PROVIDER=mock` — restores offline mock path.

### Risks
Ollama model not pulled → fallback to mock with provider note.

---

## Phase B — Expert Model Routing (complete)

### New file
- `omeia/api/expert_model_router.py`

### Changes
- Category-first routing: oncology, spatial, literature, bioinformatics, wet-lab
- Term-based fallback when no category match
- Provenance in response: `expert_model`, `expert_route_reason`, `expert_route_confidence`
- Wired through `resolve_route_model`, `chat_service`, `agent_categories`

### Feature flag
- `OMEIA_EXPERT_ROUTING_ENABLED=true`

### Tests
- `tests/test_expert_model_router.py` (5 tests)

### Linux deploy
```bash
docker exec omeia-ollama ollama pull medllama2:7b medgemma:4b meditron:7b qwen2.5:7b-instruct llama3.1:8b
```

### Rollback
`OMEIA_EXPERT_ROUTING_ENABLED=false`

---

## Phase C — Layer 1 Lab Brain MVP (complete)

### Changes
- Pipeline never auto-creates `VERIFIED` items (`from_pipeline=True`)
- Thumbs-up + citation + confidence ≥70 → `VERIFIED`
- Learning retrieval boost gated: `OMEIA_LEARNING_RETRIEVAL_BOOST=true`
- Chat responses record route metadata in `platform.ai_responses.metadata`

### Feature flags
- `OMEIA_CONTINUOUS_LEARNING_ENABLED=true`
- `OMEIA_LEARNING_RETRIEVAL_BOOST=true`

### Tests
- `tests/test_learning_verified_policy.py`

### Linux deploy
```bash
.venv/bin/python3 scripts/database/apply_sql_migrations.py   # includes 150
# restart API
```

### Rollback
Both learning flags `false` — chat continues without recording.

---

## Phase D — Research Strategy Assistant (existing + wired)

### Status
- `ResearchStrategyEngine` already implemented
- Routes when `OMEIA_RESEARCH_STRATEGY_ASSISTANT=true` and strategy question detected

### Enable
```bash
OMEIA_RESEARCH_STRATEGY_ASSISTANT=true
OMEIA_STRATEGY_REQUIRE_CITATIONS=true
```

### Tests
- `tests/test_research_strategy_engine.py` (existing)

---

## Phase E — Lab Knowledge Threads (scaffold complete)

### New files
- `omeia/api/lab_knowledge_threads.py`
- `sql/151_lab_knowledge_threads.sql`
- API: `POST /api/learning/threads`, `GET .../threads/{id}`, `POST .../challenge`

### Feature flag
- `OMEIA_LAB_KNOWLEDGE_THREADS=true`

### UI
- Thread UI hooks pending in `ChatWidget.jsx` / `OrchestratorAnswerView.jsx`

---

## Phase F — Project Intelligence Briefs (scaffold complete)

### New file
- `omeia/api/project_intelligence_briefs.py`
- API: `POST /api/learning/project-briefs`

### Feature flag
- `OMEIA_PROJECT_INTELLIGENCE_BRIEFS=true` (default off)

---

## Phase G — External Cancer Evidence (scaffold complete)

### New file
- `omeia/api/external_cancer_evidence.py` — Europe PMC metadata connector
- Merged in `SearchService.hits_for_copilot` when enabled

### Feature flag
- `OMEIA_EXTERNAL_CANCER_EVIDENCE=false` (default off)

---

## Phase H — Evaluation Framework (partial)

### New fixture
- `tests/fixtures/ai_quality_benchmark.json`

### Existing
- `infra/scripts/search/run_ai_lab_assistant_eval.py`

---

## Phase I — OMEIA Student Model

**Not started** — requires 500–1000 verified answers per strategy doc.

---

## All new env vars (Linux `configs/.env`)

```bash
OMEIA_EXPERT_ROUTING_ENABLED=true
OMEIA_CONTINUOUS_LEARNING_ENABLED=true
OMEIA_LEARNING_RETRIEVAL_BOOST=true
OMEIA_LAB_KNOWLEDGE_THREADS=true
OMEIA_PROJECT_INTELLIGENCE_BRIEFS=false
OMEIA_EXTERNAL_CANCER_EVIDENCE=false
OMEIA_ONCOLOGY_MODEL=medllama2:7b
OMEIA_SPATIAL_MODEL=qwen2.5:7b-instruct
OMEIA_LITERATURE_MODEL=meditron:7b
OMEIA_BIOINFORMATICS_MODEL=qwen2.5:7b-instruct
OMEIA_PROTOCOL_MODEL=llama3.1:8b
CHAT_GREETING_MODEL=qwen2.5:3b
CHAT_CONVERSATION_MODEL=qwen2.5:7b-instruct
```
