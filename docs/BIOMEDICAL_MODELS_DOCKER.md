# Biomedical AI models — Docker on Linux workstation

Run heavy biomedical models on the **Linux workstation** via Docker FastAPI microservices.  
**Skipped (already dockerized):** Postgres, Qdrant, Ollama.

## Services

| Service | Port | Models | Profile |
|---------|------|--------|---------|
| `biomedical-gateway` | 8100 | catalog + health | `biomodels` |
| `biomedical-embeddings` | 8101 | PubMedBERT, BioBERT, MedCPT query/article | `biomodels` |
| `biomedical-biogpt` | 8102 | BioGPT | `biomodels-llm` |
| `biomedical-txgemma` | 8103 | TxGemma 2B | `biomodels-llm` |
| `biomedical-geneformer` | 8110 | Geneformer | `biomodels-singlecell` |
| `biomedical-scgpt` | 8111 | scGPT-human | `biomodels-singlecell` |
| `biomedical-scprint` | 8112 | scPRINT | `biomodels-singlecell` |

Models download lazily on first request into Docker volume `omeia-hf-cache`.

## Linux setup

```bash
cd ~/data4TB/digital-notepad
git pull

# Embeddings only (CPU, ~2GB RAM after first model load):
BIOMODEL_PROFILES=biomodels ./scripts/docker/setup_biomodels_docker.sh

# + BioGPT + TxGemma (GPU recommended):
BIOMODEL_PROFILES=biomodels,biomodels-llm ./scripts/docker/setup_biomodels_docker.sh

# + single-cell foundation models:
BIOMODEL_PROFILES=biomodels,biomodels-llm,biomodels-singlecell ./scripts/docker/setup_biomodels_docker.sh
```

Optional HuggingFace token for gated models:

```bash
export HF_TOKEN=hf_...
```

## Mac thin client

Stop running Docker on Mac. Point API to Linux via Tailscale:

```env
DOCKER_LOCAL=false
TAILSCALE_LINUX_IP=100.80.231.55
BIOMEDICAL_MODELS_GATEWAY_URL=http://100.80.231.55:8100
BIOMEDICAL_EMBEDDINGS_URL=http://100.80.231.55:8101
BIOMEDICAL_BIOGPT_URL=http://100.80.231.55:8102
BIOMEDICAL_TXGEMMA_URL=http://100.80.231.55:8103
```

On Linux, expose to tailnet if needed:

```bash
export BIOMED_GATEWAY_BIND=0.0.0.0
./scripts/network/linux_fix_tailscale_inbound.sh
```

## API endpoints (OMEIA backend proxies)

| Method | Path |
|--------|------|
| GET | `/api/biomedical-models/catalog` |
| GET | `/api/biomedical-models/status` |
| POST | `/api/biomedical-models/embed` |
| POST | `/api/biomedical-models/generate/biogpt` |
| POST | `/api/biomedical-models/generate/txgemma` |

Direct Docker service examples:

```bash
curl http://127.0.0.1:8100/catalog
curl -X POST http://127.0.0.1:8101/embed -H 'Content-Type: application/json' \
  -d '{"texts":["ovarian cancer immunotherapy"],"model":"medcpt-query"}'
```

## Qdrant integration

Use MedCPT/PubMedBERT embeddings from `biomedical-embeddings` when indexing into existing Qdrant (`QDRANT_URL` unchanged). Set:

```env
TEXT_EMBEDDING_MODEL=medcpt-query
BIOMEDICAL_EMBEDDINGS_URL=http://127.0.0.1:8101
```

## Ollama overlap

Ollama already provides `medgemma`, `meditron`, `medllama2` for chat. **TxGemma** and **BioGPT** are separate HuggingFace services for structured biomedical generation.

## Limitations (v1)

- Single-cell services use HF fallback embeddings until native Geneformer/scGPT/scPRINT forward passes are wired.
- GPU services need NVIDIA Container Toolkit on Linux.
- First request per model is slow (download + load).
