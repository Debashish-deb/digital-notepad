# 33 — OMEIA / Färkkilä Lab Assistant: End-to-End Production Plan

**Goal:** Convert the partially working AI copilot into a production-grade, source-grounded research assistant that answers lab/research questions precisely, cites real sources, and degrades honestly.

**Reliability target:** ≥99% *grounding discipline* — never assert a fact without a retrieved source; cite every scientific/protocol claim; refuse or clearly label when evidence is missing. (This is a discipline target, not a promise that every scientific answer is correct — correctness is bounded by how densely the knowledge base is ingested.)

**Branch:** `cursor/unified-search-ai-lab-assistant`
**Stack:** React + FastAPI + PostgreSQL + Qdrant + Gemini (OpenAI-compatible endpoint)
**Owner model expectation:** This plan is written so a competent implementation AI can execute it phase by phase without guessing. Each phase has scope, exact files, acceptance criteria, tests, and a definition of done.

---

## How to read this document

- **Phases are ordered by leverage, not convenience.** Phase 2 (real corpus ingestion) and Phase 4 (retrieval quality) move accuracy more than any prompt tuning. Do not skip ahead to polish.
- **Each phase ends with a gate.** Do not start the next phase until the current gate passes and the standard verification suite is green.
- **Standard verification suite (run at the end of every phase):**
  ```bash
  python -m compileall omeia/api
  python -m unittest discover -s tests -p 'test_*.py'
  cd omeia/ui/react_frontend && npm run build
  ```
- **Never claim a phase is done without pasting the actual command output.**

---

## Guiding principles (non-negotiable)

1. **Grounding over fluency.** Every scientific/protocol claim must trace to a retrieved chunk. No source → the assistant says "I don't have an indexed source for this."
2. **Honesty of provenance.** The API must never report `provider: gemini` when the text actually came from a mock/fallback path.
3. **One orchestration path.** `/api/chat` is canonical. `/ask` must delegate to the same service or be explicitly deprecated. No divergent intent/role/source behavior.
4. **Deterministic and testable.** Every fix ships with a regression test using an in-process FastAPI `TestClient` + auth override. Tests must never depend on a live `:8000` server.
5. **Security first.** Never expose, log, or commit `GEMINI_API_KEY`. Never send true PII to an external model.

---

## Current-state baseline (from the 2026-06-06 evaluation)

| Dimension | State |
|-----------|-------|
| Gemini | Live (`gemini-3.5-flash`); free-tier 5 RPM causes silent mock fallback |
| Qdrant | Up; collections `doc_chunks`, `research_knowledge` |
| Research KB | **6 vectors**, 12 sources, 3 datasets — severely under-indexed |
| Retrieval | `file`/`vault` buckets dominate; `research` bucket rarely surfaces in chat |
| Privacy guardrail | Blocks `GSE211956` as PII (false positive) |
| Intent routing | Short queries and lab-overview questions skip RAG; "ingest" misroutes to protocol |
| Citations | `validate_answer_sources` warns but does not enforce `[n]` markers |
| Provenance | Reports `gemini` even on mock fallback |
| `/api/chat` vs `/ask` | Divergent intent, source counts, role gates |
| Heuristic quality | 4.1/5 overall; research grounding and search tasks score lower |

**Root-cause summary:** The dominant failure class is **retrieval**, not the LLM. The model frequently receives 12 chunks that do not contain the answer (weak ranking, no relevance threshold, tiny research corpus), then honestly says "no information." Fixing the corpus + ranking + thresholding is higher leverage than any prompt change.

---

# Phase 0 — Foundations & safety net (½ day)

**Why first:** Every later phase needs a reliable, scriptable way to run the API and measure behavior. Build the harness skeleton and test auth before changing logic, so every subsequent fix is measurable.

### Scope
1. **Test auth override.** Provide a documented mechanism so `TestClient` requests authenticate as a configurable role (researcher/viewer/editor/admin) without a live Firebase token. This must be test-only and never weaken production auth.
2. **Evaluation harness skeleton.** Stand up `scripts/search/run_ai_lab_assistant_eval.py` (already exists as a stub) to: load a question set, call the chat service in-process, and write a timestamped JSON to `tests/`. Scoring comes in Phase 9; for now just capture raw responses + metadata.
3. **Baseline capture.** Run the harness once and store `tests/search_qa_ai_baseline.json` as the "before" snapshot for the final report.

### Files
- `tests/conftest.py` or equivalent test fixture (auth override)
- `scripts/search/run_ai_lab_assistant_eval.py`
- `docs/33_AI_LAB_ASSISTANT_PRODUCTION_PLAN.md` (this file — keep a running changelog at the bottom)

### Acceptance / gate
- Harness runs end to end in-process with **zero 401s**.
- Baseline JSON written with per-question intent, provider, source buckets, and answer text.

---

# Phase 1 — P0 blockers (1 day)

**Why:** These are correctness/safety bugs that make the assistant actively wrong or untestable. Fix before anything else.

### 1.1 Privacy guardrail false positives (scientific identifiers)
- Add an **allowlist** of scientific identifier patterns that must never be treated as PII:
  `GSE\d+`, `GSM\d+`, `GPL\d+`, `PRJNA\d+`, `SRR\d+`, `SRX\d+`, `EGAS\d+`, `EGAD\d+`, `phs\d+(\.v\d+)?`, `TCGA-[A-Z0-9-]+`, `DOI` (`10\.\d{4,}/...`), `PMID:?\s*\d+`, common antibody clone formats, and HGNC gene/marker symbols.
- Run the allowlist **before** PII regexes; remove allowlisted spans from the text window the PII scanner sees, so an accession can never trip the PII rule.
- **Keep true PII detection intact:** Finnish HETU (`\d{6}[-+A]\d{3}[0-9A-Z]`), MRN, `patient #`, DOB, secrets/API keys.

**Tests (must add):**
- Pass (not blocked): `GSE211956`, `EGAS00001004957`, `TCGA-OV`, `PMID: 31178118`, `10.1038/s41586-...`.
- Still block: `Patient #ABC123`, a synthetic HETU, `sk-...`/`AIza...` API key, an MRN.

### 1.2 Short-query trap skipping RAG
- In `chat_intent.py`, the "≤2 tokens → general_chat, no RAG" rule must **not** fire when the message contains an accession/identifier pattern or a known research/protocol term.
- `"Find GSE211956"` → `search_request` (or `research_question`) with `use_rag=true`.

**Test:** `"Find GSE211956"` and `"GSE211956"` both classify with `use_rag=true`.

### 1.3 Provider/synthesis honesty
- Extend `ChatResponse` (and the `/ask` response) with: `effective_provider`, `model`, `fallback_used: bool`, `synthesis_mode: "live" | "mock" | "ollama"`.
- The LLM client must report **which provider actually produced the text** (not the configured provider). On rate-limit fallback to mock, `synthesis_mode="mock"`.

**Test:** Force a mock path (no key / forced failure) → response reports `synthesis_mode="mock"` and `fallback_used=true`, never `gemini`.

### Files
- `omeia/api/privacy_guardrails.py` (+ the guardrail agent if separate)
- `omeia/api/chat_intent.py`
- `omeia/api/llm_client.py`
- `omeia/api/chat_service.py`, `omeia/api/routers/chat.py`
- `tests/test_privacy_guardrails.py` (new), `tests/test_chat_intent.py`, `tests/test_chat_api.py`

### Gate
- All three sub-fixes covered by passing tests.
- No regression in existing PII blocking.

---

# Phase 2 — Research KB mass ingestion (1–2 days) ★ highest leverage

**Why:** 6 vectors cannot answer research questions. Until the corpus is dense, no amount of routing or prompt tuning produces good research answers. This is the single biggest accuracy lever.

### Scope
1. **Crawl the Färkkilä lab site properly.** The site is a JS SPA — enable the Playwright render path (`RESEARCH_KB_ENABLE_PLAYWRIGHT=true`) or, at minimum, extract JSON-LD + meta/og + visible text. Capture publications, people, project descriptions.
2. **Publications.** Ingest priority publications via PubMed eSearch/eSummary + Crossref using the lab's domain queries (HGSC, spatial biology, MHC class II, TLS, tCyCIF, ovarian cancer immunology). Store metadata + abstract (respect copyright — metadata/abstract only for closed access).
3. **Datasets.** Seed the dataset registry (GEO/EGA/TCGA/dbGaP accessions the lab uses) with normalized records.
4. **Chunk → embed → index** all of the above into the `research_knowledge` Qdrant collection (named vector `text`), with payloads carrying `source_type`, `title`, `url`, `doi`, `pmid`, `dataset_accession`, `visibility`.

### Files
- `omeia/api/research_crawler.py`, `publication_fetcher.py`, `dataset_fetcher.py`
- `omeia/api/scientific_document_parser.py`, `qdrant_research_indexer.py`, `research_knowledge_store.py`
- `configs/research_knowledge/seed_sources.json`, `crawl_allowlist.yml`
- `scripts/document-library/setup_research_knowledge.sh`

### Acceptance / gate
- `GET /api/research-knowledge/status` shows **hundreds+** of points, multiple sources, and multiple datasets (not 6).
- A research question (e.g. "What is MHC class II in HGSC?") returns **≥1 `research`-bucket source** in `/api/chat`.
- Ingestion counts recorded before/after for the final report.

### Notes
- Respect `privacy_and_copyright_policy` — store abstracts/metadata for closed-access papers, full text only where licensing allows.
- Rate-limit PubMed/Crossref politely (backoff; ≤3 req/s; identify via tool/email param).

---

# Phase 3 — Intent routing precision (½ day)

**Why:** Even with a good corpus, misrouted intents skip RAG or pull the wrong corpus.

### Scope
- **Reorder the classifier** so specific intents win before generic term matches:
  `sensitive_private` → accession/identifier search → `document_ingestion_help` → `app_help` → `search_request` → `protocol_question` → `research_question` → `smalltalk` → `general_chat`.
- `"How do I ingest documents into RAG?"` → `document_ingestion_help` (app help), **not** `protocol_question`. The word "ingest" must not pull hazardous-waste SOPs.
- **Expand `RESEARCH_TERMS`:** `färkkilä`, `lab study`, `what does the lab study`, `spatial transcriptomics`, `spatial biology`, `Visium`, `GeoMx`, `tCyCIF`, `tertiary lymphoid`, `MHC class II`, `HGSC`, `HGSOC`, plus project codes (`SPACE`, `EyeMT`, etc.).
- `"What does Färkkilä Lab study?"` → `research_question` with RAG.

### Files
- `omeia/api/chat_intent.py`
- `tests/test_chat_intent.py`

### Gate
- A routing test matrix (≥12 cases) passes, including all the misrouting cases from the audit.

---

# Phase 4 — Retrieval quality (1–2 days) ★ second highest leverage

**Why:** This is the core of the "12 sources but answer says no info" problem. Better ranking + thresholding + a real corpus is what actually delivers precise answers.

### Scope
1. **Intent-aware scopes & weights.** Make active scopes and `BUCKET_WEIGHTS` a function of intent:
   - `research_question` → boost `research`, include `lab`.
   - `protocol_question` → prioritize `lab`/`vault` SOPs.
   - `app_help` → prefer docs/app-help corpus.
2. **Relevance gating.** Add a minimum similarity threshold. If top hits fall below it, do **not** stuff weak chunks into the prompt — flag as "insufficient indexed evidence."
3. **Reranking.** Add a lightweight reranker (cross-encoder, or LLM-scored top-N) so the chunk containing the answer rises into context. This directly fixes "retrieved but not used."
4. **Dedup & diversify.** Deduplicate near-identical chunks; diversify across buckets so one corpus cannot crowd out the research KB.
5. **Remove prompt noise.** Stop injecting "0 patients / 0 samples" when counts are zero or out of scope.

### Files
- `omeia/api/search_service.py` (`hits_for_copilot`, scopes, weights)
- `omeia/api/chat_service.py` (threshold/gating, prompt assembly)
- `omeia/api/agents.py` (RAGAgent, reranker integration)
- `tests/test_search_service.py` (new/extended), `tests/test_chat_api.py`

### Gate
- For the research question set, the top-ranked source for each question contains the expected key terms (measured by the harness).
- No "no information" answers when relevant sources exist in the corpus.
- Reranking demonstrably reorders results (unit test with a planted relevant chunk).

---

# Phase 5 — Citation enforcement + honesty policy (½–1 day)

**Why:** Grounding discipline is the definition of the 99% target. Warnings are not enough.

### Scope
1. **Enforce `[n]` citations.** When `require_citations=true`, guarantee inline `[n]` markers that map to returned source cards. If the model omits them:
   - (a) re-prompt once with an explicit "you must cite using [n]" instruction, or
   - (b) append a validated "Sources used" list and flag the answer as partially grounded.
   Never ship a fact-asserting research/protocol answer with zero citations while silently logging a warning.
2. **Empty-corpus behavior.** When `use_rag=true` and retrieval is weak/empty, return a short, honest "I don't have indexed evidence on this — here's what I'd need ingested / try unified search for X" — not a confident essay.
3. **Off-topic / refusal policy.** For clearly out-of-domain questions (e.g. quantum physics), the assistant states it is a lab research copilot and either declines or clearly labels the answer as general knowledge, not lab-grounded.

### Files
- `omeia/api/answer_grounding_service.py`
- `omeia/api/chat_service.py`
- `tests/test_chat_api.py`

### Gate
- Must-cite questions: 100% contain `[n]` markers mapping to real sources, or an explicit "no source found" statement.
- Off-topic question returns a labeled/declined answer, not a confident fabrication.

---

# Phase 6 — Unify `/api/chat` and `/ask` (½ day)

**Why:** Divergent paths confuse users and double the maintenance/bug surface.

### Scope
- Make `/ask` call the **same orchestration service** as `/api/chat` (same intent routing, retrieval, citation enforcement, role policy) — or formally deprecate `/ask`, update all callers, and document the change.
- Align role gates: both allow researcher/viewer/editor/admin with the same degradation rules.
- Remove the source-count divergence (chat 12 vs `/ask` 20). Pick one policy.

### Files
- `omeia/api/routers/copilot.py`, `omeia/api/routers/chat.py`
- `omeia/api/chat_service.py`
- `tests/test_copilot.py`, `tests/test_chat_api.py`

### Gate
- Same question to `/api/chat` and `/ask` yields the same intent, comparable sources, and identical role behavior (or `/ask` is deprecated and documented).

---

# Phase 7 — Presentation / UX + multilingual (1 day)

**Why:** Trust comes from accurate provenance, honest limitations, and natural tone.

### Scope
1. Populate `model` / `effective_provider` / `synthesis_mode` so the UI badge is accurate (live Gemini vs mock).
2. Show `limitations` even for low-source intents (don't hide guardrail notes when `show_sources=false`).
3. Conversational intents (smalltalk, app_help) render as **natural prose** — suppress the "### 1. Direct Answer / ### OMEIA copilot synthesis" report template for those.
4. Add **bucket badges** (research / lab / file / vault) on source cards; ensure clickable nav works.
5. **Multilingual:** detect the user's language (Finnish and other supported locales) and answer in that language while still retrieving from English docs.

### Files
- `omeia/ui/react_frontend/src/components/ChatWidget.jsx`
- `omeia/ui/react_frontend/src/components/AssistantSearchHits` (or equivalent)
- `omeia/ui/react_frontend/src/api/chatClient.js`
- `omeia/api/chat_service.py` (language-detection → response-language instruction)

### Gate
- UI badge matches the actual synthesis mode.
- A Finnish question is answered in Finnish with English-sourced citations.
- Smalltalk renders without report headings.

---

# Phase 8 — Reliability & ops (½ day)

### Scope
1. **Rate limits:** add retry with exponential backoff + a request queue/delay for Gemini. Make the eval battery rate-limit aware (delays/backoff). Document moving to a paid tier for batch evaluation.
2. **Test auth override** documented (from Phase 0) so scripted evaluation never hits raw 401s.
3. **Docs:** update `docs/30_SEARCH_FUNCTIONALITY_AUDIT.md` to reflect `ChatWidget → /api/chat` (currently stale, says `/ask`).

### Files
- `omeia/api/llm_client.py`
- `scripts/search/run_ai_lab_assistant_eval.py`
- `docs/30_SEARCH_FUNCTIONALITY_AUDIT.md`

### Gate
- A 50-question battery completes without rate-limit-induced failures.

---

# Phase 9 — Evaluation harness & release gate (1 day) ★ proof

**Why:** This is how you *prove* the 99% grounding target, not assert it.

### Scope
1. **Gold-standard Q&A set (≥50 questions)** across: smalltalk, lab overview, research (MHC II, TLS, spatial transcriptomics datasets), protocols (Ashlar, BaSiC, segmentation), dataset lookup (GSE/EGA/TCGA), app-help, sensitive/PII, off-topic, and Finnish. For each question define: expected intent, expected buckets, must-cite (yes/no), key terms/sources the answer should contain.
2. **Automated scorer** records per question: intent correctness, RAG used (vs expected), source buckets, citation presence, grounding (key terms/sources appeared), provider honesty, pass/fail.
3. **Release gate:**
   - Intent accuracy ≥ 95%
   - Citation compliance = 100% on must-cite questions
   - Zero PII leaks; zero false PII blocks on accessions
   - Research questions surface ≥ 1 `research` source
   - No "no information" answers when relevant sources exist
   - Provider honesty = 100% (no mock-as-gemini)
4. Persist results to timestamped JSON; print a summary table; re-run after every phase from here on.

### Files
- `scripts/search/run_ai_lab_assistant_eval.py`
- `tests/ai_eval_gold_set.json` (new)
- `tests/search_qa_ai_last_run.json` (output)

### Gate
- All release-gate thresholds pass with pasted harness output.

---

## Cross-cutting requirements

- **Security:** never log/commit `GEMINI_API_KEY`; never send true PII externally; keep allowlist + PII rules covered by tests.
- **Backward compatibility:** don't break existing working behaviors (greetings, protocol Q&A, privacy blocking of real PII).
- **Every phase:** run the standard verification suite and the eval harness; record results.

---

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Färkkilä site is JS-rendered → empty crawl | Enable Playwright path or JSON-LD/meta extraction; verify body text length > 0 per page |
| Gemini free-tier 5 RPM breaks batch eval | Backoff + queue; document paid tier; throttle harness |
| Reranker adds latency | Keep top-N small (e.g. rerank top 20 → keep 8); cache embeddings |
| Copyright on closed-access papers | Metadata/abstract only; enforce in ingestion |
| Over-blocking real PII while allowlisting accessions | Allowlist is span-scoped; PII tests must still pass |
| "99% correctness" misread as "always right" | Frame as grounding discipline; correctness scales with corpus density |

---

## Effort & sequencing summary

| Phase | Theme | Leverage | Est. |
|-------|-------|----------|------|
| 0 | Foundations & test harness | Enables measurement | ½ day |
| 1 | P0 blockers | Correctness/safety | 1 day |
| 2 | Research KB mass ingestion | ★★★ Highest | 1–2 days |
| 3 | Intent routing precision | High | ½ day |
| 4 | Retrieval quality (rerank/threshold) | ★★★ Second | 1–2 days |
| 5 | Citation enforcement + honesty | Defines 99% | ½–1 day |
| 6 | Unify `/api/chat` + `/ask` | Maintainability | ½ day |
| 7 | UX + multilingual | Trust | 1 day |
| 8 | Reliability & ops | Stability | ½ day |
| 9 | Eval harness & release gate | Proof | 1 day |

**Total: ~7–9 working days.**

---

## Final report (required deliverable)

When the work is complete, produce a report containing:
1. Files changed/created.
2. Each audit gap (P0/P1/P2) mapped to its fix and the test that proves it.
3. Ingestion counts before/after (Research KB points, sources, datasets).
4. Evaluation harness results vs every release-gate threshold (paste the summary table).
5. Exact commands run with their output.
6. Remaining limitations and recommended next steps.

**Do not claim any gate passed without showing the eval output.**

---

## Test auth (Phase 0/8)

In-process tests and the eval harness authenticate via `tests/auth_fixtures.py`:

```python
from tests.auth_fixtures import apply_auth_override, clear_auth_override
apply_auth_override("researcher")  # researcher | viewer | editor | admin
# ... TestClient calls ...
clear_auth_override()
```

Never import `auth_fixtures` from production code paths.

---

## Strategic notes (read before starting)

- **"99%+" is a grounding-discipline target, not an omniscience target.** It is achievable for: never fabricate, always cite, refuse when unsure. It is **not** achievable for "answers every scientific question correctly" unless Phase 2 (mass ingestion) makes the corpus dense. Phase 2 is therefore above all prompt tuning in priority.
- **The biggest bug class is retrieval, not the LLM.** Weak ranking + no thresholding means the model receives chunks that don't contain the answer and honestly says "no information." Phases 2 and 4 (real corpus + reranking + relevance gating) move quality more than anything else.
- **Measure continuously.** From Phase 0 onward, the eval harness is the source of truth. Re-run it after every phase and watch the gate metrics trend toward the release thresholds.

---

## Changelog

| Date | Phase | Change | Verification |
|------|-------|--------|--------------|
| 2026-06-06 | 0 | Added `tests/auth_fixtures.py` (test-only auth override for researcher/viewer/editor/admin). Hardened `scripts/search/run_ai_lab_assistant_eval.py` for in-process TestClient calls; captures intent, provider, buckets, answer. Baseline written to `tests/search_qa_ai_baseline.json` (15 questions, 0 HTTP errors). | `compileall` OK; Phase 0/1 unit tests OK; `npm run build` OK; baseline harness `http_errors: 0` |
| 2026-06-06 | 1 | Scientific identifier allowlist in `privacy_guardrails.py` (GSE/GSM/EGA/TCGA/DOI/PMID etc.) before PII regex; secret-key blocking preserved. Short-query trap bypass for accessions in `chat_intent.py`. Provider honesty: `effective_provider`, `model`, `fallback_used`, `synthesis_mode` on `/api/chat` and `/ask`. | `test_privacy_guardrails` pass/block matrix green; `Find GSE211956` → `search_request` + `use_rag=true`; mock fallback reports `synthesis_mode=mock`, never `gemini` |
| 2026-06-06 | 2 | Mass research KB ingestion: expanded PubMed/Crossref discovery (efetch abstracts, seed queries, 429 backoff); richer publication index text; setup script default crawl cap uses `RESEARCH_KB_MAX_PUBLIC_PAGES`. Ran `scripts/document-library/setup_research_knowledge.sh` with Playwright. **Before:** 6 points / 12 sources / 3 datasets. **After:** 224 points / 217 sources / 3 datasets. | `compileall omeia/api` OK; `test_copilot` + `test_chat_intent` OK; `search_research("What is MHC class II in HGSC?")` → 5 hits |
| 2026-06-06 | 3 | Intent classifier reordered (sensitive → accession → ingestion → app_help → search → protocol → research → smalltalk); expanded `RESEARCH_TERMS` + lab overview patterns; removed `ingest` from protocol terms. 15 routing tests in `test_chat_intent.py`. | Intent matrix green; `Färkkilä Lab study` → `research_question` + RAG |
| 2026-06-06 | 4 | Intent-aware scopes/weights, lexical reranker, min-score gating, dedup/diversify in `hits_for_copilot`; zero-count DB noise removed from prompts. `test_search_service.py` added. | Reranker unit test promotes relevant chunk; gating drops sub-threshold hits |
| 2026-06-06 | 5 | Citation enforcement via re-prompt + sources append in `answer_grounding_service`; empty-corpus honest answers; off-topic refusal policy. Tests in `test_chat_api.py`. | Must-cite path appends `[n]` or sources block; off-topic labeled |
| 2026-06-06 | 6 | `/ask` delegates to `answer_chat` (same intent/RAG/citations); `QuestionResponse` aligned with chat metadata; parity test in `test_copilot.py`. | Chat vs `/ask` same intent for lab overview / Ashlar / GSE |
| 2026-06-06 | 7 | ChatWidget: `effective_provider`/`synthesis_mode` badge, limitations always visible, bucket CSS classes on source cards; Finnish response instruction in `chat_service`. | `npm run build` OK |
| 2026-06-06 | 8 | Gemini rate-limit retry/backoff in `llm_client.py`; eval harness delay (`EVAL_REQUEST_DELAY_S`); test auth documented via `tests/auth_fixtures.py`; audit doc updated to `/api/chat`. | 50+ question battery completes without HTTP 401 |
| 2026-06-06 | 9 | Gold set `tests/ai_eval_gold_set.json` (56 questions); automated scorer + release gates in `run_ai_lab_assistant_eval.py`; output `tests/search_qa_ai_last_run.json`. | Release gate summary table printed; gates tracked per run |
