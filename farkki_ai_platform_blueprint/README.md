# Farkki-AI Clinical & Spatial Biology Research Platform Blueprint

An end-to-end framework and live prototype for a cancer and spatial-biology AI analysis platform. Farkki-AI serves as the centralized intelligence and search layer for consolidating high-plex spatial imaging (tCyCIF), multiplex spatial transcriptomics (GeoMx), next-generation sequencing (WES, scRNA-seq), and clinical registries.

---

## 🌌 The Grand Master Plan

The vision of the **Farkki-AI Platform** is to accelerate precision oncology discovery in ovarian cancer (specifically High-Grade Serous Ovarian Cancer - HGSC) by structuring high-quality cohort datasets into a unified spatial knowledge network. 

### 1. Core Paradigm: Structured Extraction & Citation
Traditional LLM integration in bioinformatics often fails due to hallucinated statistics or un-auditable outputs. Farkki-AI enforces a strict hierarchy:
```text
Raw Cohort Data (tCyCIF, GeoMx, WES)
  → Validated Preprocessing Pipelines (LUMI/Workstation Snakemake)
  → Standardized Feature Extraction (Single-cell tables, spatial networks)
  → Statistics / Graph / Vector / Retrieval Tools
  → LLM Explanation and Semantic Translation Layer (RAG)
  → Cited Answers with complete Reproducibility Traces
```
**Safety Guardrail:** The LLM does *not* compute statistics (hazard ratios, p-values, sample counts) directly. These are fetched from Postgres or pre-computed analysis runs, and translated into conversational text.

### 2. Multi-Modal Integration
Farkki-AI maps data elements into four distinct layers:
* **Relational Layer (PostgreSQL)**: Handles structured metadata—projects, cohorts, specimens, clinical variables (platinum sensitivity, PFS, OS), and data lineage.
* **Vector Layer (Qdrant)**: Indexes unstructured knowledge—SOPs, experimental protocols, meeting logs, publications, and raw script/codebase logic.
* **Graph Layer (Neo4j)**: Maps biological and spatial relationships—cell-to-cell interaction networks, pathway associations, and lineage links.
* **Object Store (MinIO)**: Archives heavy binary outputs—stitched OME-TIFFs, cell segmentations, and raw feature matrices.

---

## ⚡ Current Development State (Phase 2 Completed)

We have successfully migrated the blueprint from a skeleton mock into a fully functional local development stack running live services:

### 1. Active Services Stack (Docker Compose)
* **PostgreSQL (Port 5432)**: Active with the complete multi-schema layout (`core`, `clinical`, `assay`, `features`, `rag`, `spatial`).
* **Qdrant (Port 6333)**: Configured with custom collection indexes for `doc_chunks` and `script_chunks`.
* **Neo4j (Port 7474)**: Initialized for network mapping.
* **MinIO (Port 9000)**: Active for artifact and image file uploads.

### 2. Ingested Data Registry
* **Structured Cohort**: 20 synthetic patient profiles with survival metadata (PFS, OS, HRD indicator, BRCA mutation indicator) and 40 sample records representing multiplex assay types mapped inside `core` tables.
* **Documentation Registry**: 130 markdown blocks covering all 10 architectural and SOP guidelines inside the `docs/` folder embedded into Qdrant.
* **Script Registry**: 2058 function and script snippets from 11 consolidated research project repositories embedded into Qdrant.

### 3. Integrated RAG API Backend (FastAPI)
* Running on `http://localhost:8000`.
* Features hybrid query resolution: queries Qdrant using a custom 384-dimensional pseudo-semantic bag-of-words vectorizer and queries Postgres for metadata counts to prevent hallucinations.

### 4. Interactive Streamlit Dashboard (Streamlit)
* Running on `http://localhost:8501`.
* **Chat Copilot**: User query field featuring automatic citations, confidence scoring, and alert flags.
* **Database Explorer**: Live metrics cards and bar charts fetching active statistics directly from PostgreSQL.
* **Document Catalog**: Vector searching directly inside Qdrant collections.

---

## 📂 Repository Layout

```text
├── docs/                      # Platform architecture and design guidelines (Ingested)
├── sql/                       # PostgreSQL schemas, indexes, and init scripts
├── configs/                   # Docker Compose, environment configurations, and yaml definitions
├── schemas/                   # CSV manifest templates for registry verification
├── scripts/                   # Seeding, ingestion, validation, and testing scripts
│   ├── create_qdrant_collections.py  # Sets up vector collections
│   ├── ingest_database.py            # Seeds PostgreSQL with synthetic registries
│   ├── ingest_documents_demo.py      # Chunks and embeds docs and scripts to Qdrant
│   ├── query_copilot_demo.py         # Terminal verification search utility
│   └── synthetic_seed_data.py        # Generates synthetic data files
├── app_skeleton/
│   ├── api/
│   │   ├── main.py            # FastAPI main app serving database and vector endpoints
│   │   └── requirements.txt   # Backend python package dependencies
│   └── ui/
│       └── streamlit_app.py   # Streamlit dashboard script
└── task.md                    # Project tracking checklist
```

---

## 🚀 Quickstart Guide

To run and verify the complete Farkki-AI stack locally:

### 1. Boot up Docker Services
Spin up PostgreSQL, Qdrant, Neo4j, and MinIO in the background:
```bash
docker compose -f configs/docker-compose.dev.yml up -d
```

### 2. Set Up Virtual Environment & Dependencies
Initialize Python virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r app_skeleton/api/requirements.txt
```

### 3. Ingest Registries and Documents
Create Qdrant collections, generate synthetic registries, and embed files:
```bash
# Initialize vector collections
python scripts/create_qdrant_collections.py

# Generate synthetic CSV datasets
python scripts/synthetic_seed_data.py

# Ingest CSV registries into PostgreSQL
python scripts/ingest_database.py

# Ingest documentation and scripts into Qdrant
python scripts/ingest_documents_demo.py
```

### 4. Launch the Applications
Run the FastAPI backend server:
```bash
.venv/bin/uvicorn app_skeleton.api.main:app --host 0.0.0.0 --port 8000
```
In a separate terminal, launch the Streamlit frontend dashboard:
```bash
.venv/bin/streamlit run app_skeleton/ui/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

Open [http://localhost:8501](http://localhost:8501) in your browser to interact with the platform dashboard!

---

## 🔒 Security & Data Redaction Guardrails
Always abide by the platform rules defined in `docs/06_SECURITY_GOVERNANCE.md`:
* **No Direct Identifiers**: Never ingest patient names, social security numbers, medical record numbers, or exact dates.
* **Sensitivity Scopes**: Data queries are strictly scoped by project code filters (`SPACE`, `EyeMT`, `KRAS`) to ensure researchers can only retrieve information they have permissions to access.
