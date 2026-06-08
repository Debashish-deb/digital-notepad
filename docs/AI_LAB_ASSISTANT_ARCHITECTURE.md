# OMEIA AI Lab Assistant — Architecture (Mermaid)

Corrected flowcharts for external review (GPT / Claude).  
**Mermaid rules applied:** arrows connect to **nodes**, not subgraph labels; no stray punctuation after `end`; dead-end nodes wired; routing labels match code.

**Code anchors:** `ChatWidget.jsx` → `POST /api/chat/category` → `answer_chat` (fast/balanced) or `run_category_chat` (deep); `GlobalSearchOverlay` → `GET /api/platform/unified-search` (separate from copilot RAG).

---

## 1. End-to-end copilot request (primary path)

```mermaid
flowchart TB
    subgraph CLIENT["Frontend — Mac thin client"]
        CW["ChatWidget.jsx<br/>AI Assistant → Copilot"]
        SEL["User context<br/>• project_codes EyeMT SPACE KRAS<br/>• agent category oncology / spatial / …<br/>• mode fast | balanced | deep<br/>• library_scope optional"]
        GSO["GlobalSearchOverlay ⌘K<br/>omnibox — not copilot"]
        CW --> SEL
    end

    subgraph AUTH["Security boundary"]
        FB["Firebase ID token<br/>farkki_id_token"]
        RPU["require_platform_user"]
        RR["require_role<br/>researcher | viewer | editor | admin"]
        RL["Rate limiter"]
        FB --> RPU --> RR --> RL
    end

    subgraph API["FastAPI routers"]
        CAT["POST /api/chat/category<br/>primary UI path"]
        CHAT["POST /api/chat<br/>POST /api/chat/stream<br/>legacy stream path"]
        ASK["POST /ask<br/>legacy / debug"]
        USEARCH["GET /api/platform/unified-search<br/>omnibox only"]
        DBG["POST /api/chat/rag-debug<br/>diagnostics"]
    end

    SEL --> CAT
    CAT --> FB
    GSO --> USEARCH
    USEARCH --> FB
    SEL -.->|legacy model picker| CHAT
    CHAT --> FB
    SEL -.->|debug| ASK
    ASK --> FB

    subgraph ROUTE["Category routing decision"]
        UNI{"CATEGORY_UNIFIED_EVIDENCE=true<br/>AND mode ∈ fast,balanced?"}
        AC["answer_chat — single evidence pipeline"]
        MC["run_category_chat — multi-agent<br/>when deep OR unified off"]
        UNI -->|yes fast/balanced| AC
        UNI -->|deep or unified off| MC
    end

    RL --> UNI

    subgraph PIPE["answer_chat pipeline"]
        I1["1 classify_and_enrich<br/>chat_intent.py"]
        I2["2 understand_query<br/>evidence_orchestrator.py"]
        I3["3 guard_for_llm<br/>PII / MRN / secrets"]
        I4{"Short-circuit?"}
        I5["instant greeting template"]
        I6["sensitive_private refusal"]
        I7["off-topic refusal"]
        I8["4 resolve_route_model"]
        I9["5 Retrieval if use_rag"]
        I10["6 package_evidence + claim_validation"]
        I11["7 Build orchestrator prompt"]
        I12["8 llm.generate"]
        I13["9 enforce_citations retry"]
        I14["10 API response payload"]

        I1 --> I2 --> I3 --> I4
        I4 -->|greeting| I5 --> I14
        I4 -->|sensitive| I6 --> I14
        I4 -->|off-topic| I7 --> I14
        I4 -->|continue| I8 --> I9 --> I10 --> I11 --> I12 --> I13 --> I14
    end

    AC --> I1

    RAGB["build_rag_bundle<br/>shared retrieval for agents"]
    AGENTS["Sequential specialists<br/>planner → reasoner → literature → critic → synthesizer"]
    MC --> RAGB
    RAGB --> AGENTS
    AGENTS --> I14

    subgraph LLM["LLM provider layer — llm_client.py"]
        GEM["Gemini — CHAT_LLM_PROVIDER<br/>research synthesis"]
        OLL["Ollama qwen3:8b/14b<br/>greeting / conversation"]
        FBK["Fallback chain<br/>gemini→groq→openrouter→ollama→mock"]
        EMB["embed — local hash 384-d<br/>offline RAG"]
        GEM --> FBK
        OLL --> FBK
    end

    I8 --> GEM
    I8 -.->|smalltalk / general| OLL
    I12 --> GEM
    I12 -.->|routed intents| OLL
    EMB -.-> HS

    subgraph RET["Retrieval — SearchService.hits_for_copilot"]
        HS["unified_search hybrid<br/>intent-scoped buckets"]
        PAR["Parallel bucket fetch<br/>CHAT_PARALLEL_RETRIEVAL"]
        RER["Intent weights · rerank<br/>COPILOT_MIN_SCORE · dedup"]
        LEG{"CHAT_USE_LEGACY_RAG?"}
        RAGA["RAGAgent.retrieve<br/>doc_chunks fallback"]
        HS --> PAR --> RER
        RER --> LEG
        LEG -->|sparse hits| RAGA
    end

    I9 --> HS
    USEARCH --> HS

    subgraph UI_OUT["Frontend rendering"]
        OAV["OrchestratorAnswerView<br/>sections + confidence"]
        SRC["Sources [1][2]… + search_hits nav"]
        RESP["ChatWidget message thread"]
        I14 --> RESP
        RESP --> OAV
        RESP --> SRC
        USEARCH --> GSO
    end
```

**App notes**

| Topic | Behavior in code |
|--------|------------------|
| Primary UI path | `ChatWidget` default → `sendCategoryChat` → `/api/chat/category` |
| Unified evidence | `CATEGORY_UNIFIED_EVIDENCE=true` (default): fast/balanced skip multi-agent loop |
| Deep mode | `mode=deep` → `run_category_chat` even when unified is on |
| Omnibox | `GlobalSearchOverlay` → `/api/platform/unified-search` → same `SearchService`, **no LLM** |
| Deep vs pipeline | Deep agents synthesize directly; `I14` here means shared **response envelope** to the UI, not that deep runs steps 1–9 |

---

## 2. Knowledge ingestion and storage

```mermaid
flowchart LR
    subgraph SOURCES["Source systems"]
        DISK_LAB["DATABASE_ROOT<br/>lab SOPs protocols"]
        DISK_PROJ["Project folders<br/>EyeMT SPACE KRAS"]
        VAULT_FS["Vault filesystem"]
        PUB["publication_fetcher"]
        CRAWL["research_crawler"]
        UPLOAD["POST /ingest-document"]
        NB["Notebook Wiki Decisions<br/>Postgres platform.*"]
    end

    subgraph PROCESS["Processors"]
        DP["database_processor"]
        PP["project_processor<br/>digital twin JSON"]
        LKS["lab_knowledge_store"]
        RKS["research_knowledge_store"]
        VIE["vault_ingestion_engine"]
    end

    subgraph STORE["Persistent stores"]
        PG_RAG["Postgres rag.*"]
        PG_PLAT["Postgres platform.*"]
        QD_LAB["Qdrant doc_chunks<br/>lab_operations"]
        QD_RES["Qdrant research_knowledge"]
        TWIN["public/processed/*.json<br/>+ PROCESSED_DIR fallback"]
        INV["raw_asset_inventory.json"]
    end

    DISK_LAB --> DP --> LKS --> PG_RAG --> QD_LAB
    DISK_PROJ --> PP --> TWIN
    PP -.->|optional| PG_RAG
    VAULT_FS --> VIE --> PG_PLAT --> INV
    PUB --> RKS
    CRAWL --> RKS
    RKS --> PG_PLAT --> QD_RES
    UPLOAD --> PG_PLAT --> QD_LAB
    NB --> PG_PLAT
```

---

## 3. Retrieval buckets and intent routing

```mermaid
flowchart TB
    Q["Query + intent + project_codes + user_role"]

    subgraph INTENTS["chat_intent.py"]
        PQ["project_question"]
        RQ["research_question"]
        PRQ["protocol_question"]
        SQ["search_request"]
        PEQ["people_question"]
        GC["general_chat — no RAG"]
        SP["sensitive_private — blocked"]
    end

    Q --> INTENTS

    subgraph BUCKETS["SearchService.unified_search"]
        B1["project"]
        B2["file — twin document_index"]
        B3["lab — doc_chunks"]
        B4["vault"]
        B5["document_library"]
        B6["research — research_knowledge"]
        B7["notebook wiki decision task"]
        B8["people"]
    end

    subgraph PLAN["evidence_orchestrator search_plan"]
        SP1["project_question<br/>project → file → lab → research"]
        SP2["research_question<br/>research → lab → file"]
        ENR["Enriched query<br/>prepend EyeMT when detected"]
    end

    subgraph ROLES["Role access"]
        ADM["admin editor researcher<br/>include_restricted"]
        VIEW["viewer — internal only"]
    end

    PQ --> SP1 --> BUCKETS
    RQ --> SP2 --> BUCKETS
    PQ --> ENR
    Q --> ROLES
    ROLES --> BUCKETS

    EP["EvidencePackage<br/>rank · validate claims · confidence"]
    BUCKETS --> EP
    EP --> SYN["Grounded LLM synthesis"]
```

---

## 4. Multi-agent deep mode (sequence)

```mermaid
sequenceDiagram
    participant UI as ChatWidget
    participant API as POST /api/chat/category
    participant ORC as run_category_chat
    participant RAG as build_rag_bundle
    participant SS as SearchService
    participant A1 as Specialist agents
    participant SYN as Synthesizer
    participant LLM as LLM providers

    UI->>API: message category mode=deep project_codes
    API->>ORC: agents_for_category
    ORC->>RAG: if any agent.use_rag
    RAG->>SS: hits_for_copilot
    SS-->>RAG: search hits
    loop Each agent in pipeline
        ORC->>A1: generate with prior context
        A1->>LLM: preferred then fallback model
        LLM-->>A1: specialist output
    end
    ORC->>SYN: merge outputs
    SYN->>LLM: final synthesis
    LLM-->>API: answer trace_id agents_used
    API-->>UI: citations confidence limitations
```

---

## 5. Infrastructure topology

```mermaid
flowchart LR
    subgraph MAC["Mac workstation"]
        VITE["Vite React :5173"]
        API_MAC["FastAPI :8000<br/>start_portable.sh"]
        VITE --> API_MAC
    end

    subgraph NET["Tailscale"]
        TS["TAILSCALE_LINUX_IP"]
    end

    subgraph LINUX["Linux Docker stack"]
        PG["Postgres :5432"]
        QD["Qdrant :6333"]
        OL["Ollama :11434"]
    end

    API_MAC --> TS
    TS --> PG
    TS --> QD
    TS --> OL
```

---

## Review brief (for external models)

**System:** OMEIA Färkkilä Lab AI Assistant — FastAPI + React copilot with RAG over Postgres, Qdrant, and JSON project twins.

**Intended invariants**

- Scientific claims grounded in retrieved evidence with citations when `use_rag`.
- PII/secrets blocked before external LLM (`guard_for_llm`).
- Admin/editor/researcher: broader retrieval (`include_restricted`); viewer: internal only.
- Project questions: hybrid project twins + publications + lab corpus.

**Known tensions (verify)**

1. Dual RAG: `SearchService` + legacy `RAGAgent` on `doc_chunks`; vector schema may differ.
2. Weak embeddings: hashed 384-d local vectors vs true semantic models.
3. Omnibox vs copilot: unified-search shares `SearchService` but not evidence orchestrator or LLM.
4. Unified path: UI shows category team; fast/balanced run `answer_chat` only.
5. Project ingest: twins in `public/processed/`; Qdrant coverage for `project_workspace` incomplete.
6. No session memory DB — context is per-request (+ project chips).
7. Streaming: `/api/chat/stream` completes retrieval before token stream.

**Questions for reviewer**

- Is intent → bucket → evidence → LLM sound?
- Failure modes in parallel retrieval (`CHAT_PARALLEL_RETRIEVAL`)?
- Security boundary adequate for admin data vs auth secrets?
- Should omnibox and copilot share one ranking pipeline?

---

*Generated for architecture review. Mermaid validated against node-to-node linking rules.*
