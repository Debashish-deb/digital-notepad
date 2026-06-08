# OMEIA Phase Status

Last updated: June 2026. Honest snapshot vs [OMEIA_PRODUCT_UPGRADE_MASTER_PLAN.md](./OMEIA_PRODUCT_UPGRADE_MASTER_PLAN.md).

Legend: **Done** · **Partial** · **Not started**

---

## Phase 1 — Foundation: indexing, search, storage {#phase-1}

**Partial → largely done on Linux branch**

| Item | Status |
|------|--------|
| `vector_indexer.py`, `embedding_service.py`, `qdrant_collections.py` | Done |
| `SearchService` single path | Partial (legacy proxies remain) |
| Admin `/api/admin/index-health` | Done |
| Feature flags `KNOWLEDGE_INDEXER_ENABLED`, `VECTORIZATION_ENABLED`, `VAULT_JSON_FALLBACK` | Done |
| Tests `test_vector_indexer.py`, `test_search_service.py`, `test_embedding_dim_contract.py` | Done |

**Next:** Run full Linux reindex + set `VAULT_JSON_FALLBACK=false` after validation.

---

## Phase 2 — Knowledge foundation {#phase-2}

**Partial**

| Item | Status |
|------|--------|
| `knowledge_indexer.py`, `chunking.py` | Done |
| `CANONICAL_CHUNK_PIPELINE` flag | Done (default off) |
| Document lineage in Postgres | Partial |
| JSON twins UI-only | Partial |

**Next:** Enable `CANONICAL_CHUNK_PIPELINE=true` on Linux after ingest test pass.

---

## Phase 3 — OCR {#phase-3}

**Partial**

| Item | Status |
|------|--------|
| `ocr/tesseract_backend.py`, `ocr/adapter.py` | Done |
| `ENABLE_OCR` flag (default false) | Done |
| OCR queue script | Done |
| Library OCR badges | Partial |

**Next:** Linux: `apt install tesseract-ocr poppler-utils`, `ENABLE_OCR=true`, validate 3 scanned PDFs.

---

## Phase 4 — Three-layer AI {#phase-4}

**Done** — see [THREE_LAYER_IMPLEMENTATION_REPORT.md](./THREE_LAYER_IMPLEMENTATION_REPORT.md)

- Layer 2 conversation fast path
- Layer 3 `expert_model_router.py`
- Layer 1 learning MVP + threads
- `/api/chat/status`

---

## Phase 5 — Research Strategy Assistant {#phase-5}

**Partial**

| Item | Status |
|------|--------|
| `research_strategy_engine.py`, strategy agents | Done |
| `OMEIA_RESEARCH_STRATEGY_ASSISTANT` flag | Done (default off) |
| Citation grounding tests | Done |
| Full ovarian-cohort validation on Linux | Not run |

**Next:** Enable flag on Linux + run strategy eval question from master plan.

---

## Phase 6 — Continuous learning {#phase-6}

**Partial**

| Item | Status |
|------|--------|
| Feedback API, verified knowledge policy | Done |
| `OMEIA_CONTINUOUS_LEARNING_ENABLED` | Done |
| Fine-tuning | Not started (by design) |

---

## Phase 7 — Scientific image viewer {#phase-7}

**Partial**

| Item | Status |
|------|--------|
| Tile streaming API | Done |
| `ImageTileViewer.jsx`, manifest client | Done |
| Napari in React | Not started (by design) |
| Segmentation overlay in viewer | Not started |

See [IMAGE_STREAMING_API.md](./IMAGE_STREAMING_API.md), [SCIENTIFIC_IMAGE_VIEWER_REFERENCES.md](./SCIENTIFIC_IMAGE_VIEWER_REFERENCES.md).

---

## Phase 8 — External evidence {#phase-8}

**Partial**

| Item | Status |
|------|--------|
| `research_knowledge_store` external search | Done |
| `OMEIA_EXTERNAL_CANCER_EVIDENCE` | Done (default off) |
| Connector citation validation suite | Partial |

---

## Phase 9 — Security {#phase-9}

**Partial**

| Item | Status |
|------|--------|
| Firebase → researcher binding | Done |
| `PROJECT_RBAC_ENABLED` | Done (default off) |
| Image access audit | Done |
| Rate limits | Partial |

---

## Phase 10 — Frontend UX {#phase-10}

**Partial**

| Item | Status |
|------|--------|
| Document type taxonomy + list metadata | Done (recent) |
| Structured AI answer view | Partial |
| Challenge / feedback UI | Partial (threads) |
| PDF viewer 15:85 split | Done (recent, uncommitted) |

---

## Phase 11 — Linux ops {#phase-11}

**Partial**

| Item | Status |
|------|--------|
| `start_linux.sh`, `check_linux_sync_health.py` | Done |
| Backup/restore scripts | Partial |
| Admin status dashboard | Partial (Phase 14 extends) |

---

## Phase 12 — Evaluation {#phase-12}

**Partial**

| Item | Status |
|------|--------|
| `run_search_qa.py`, `run_ai_lab_assistant_eval.py` | Done |
| Quality reports under `reports/` | Partial |

---

## Phase 13 — Scientific references {#phase-13}

**Started**

- [SCIENTIFIC_REFERENCE_REGISTRY.md](./SCIENTIFIC_REFERENCE_REGISTRY.md)
- [SCIENTIFIC_IMAGE_VIEWER_REFERENCES.md](./SCIENTIFIC_IMAGE_VIEWER_REFERENCES.md)
- [ADAPTIVE_COMPUTE_PROFILES.md](./ADAPTIVE_COMPUTE_PROFILES.md)

Still needed: `AI_RETRIEVAL_REFERENCES.md`, `BIOINFORMATICS_PIPELINE_REFERENCES.md`, `SCIENTIFIC_METHOD_REFERENCES.md` (full content).

---

## Phase 14 — Adaptive compute + missing dashboards {#phase-14}

**In progress**

| Item | Status |
|------|--------|
| `compute_profile_service.py` | In progress |
| `/api/system/compute-status` | In progress |
| Admin compute panel | In progress |
| Job/evidence/model dashboards | Not started |

See [ADAPTIVE_COMPUTE_PROFILES.md](./ADAPTIVE_COMPUTE_PROFILES.md).

---

## Recommended next execution order

1. Finish Phase 14 compute status + admin panel
2. Linux validate Phase 1 reindex + Phase 3 OCR sample
3. Enable `OMEIA_RESEARCH_STRATEGY_ASSISTANT` on Linux with eval suite
4. Complete Phase 13 reference docs
5. Phase 10 structured answer UX + evidence panel
