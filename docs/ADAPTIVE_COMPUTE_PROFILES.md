# Adaptive Compute Profiles

OMEIA does **not** fake a “virtual GPU.” It selects the safest available **compute profile** per task.

## Profiles

| Profile | Typical host | LLM | Images | Heavy ML |
|---------|--------------|-----|--------|----------|
| `LOW_END_LAPTOP` | MacBook / thin client | Small local / mock | Thumbnail + tiles via API | Queued / remote only |
| `MEDIUM_LAPTOP` | 16GB RAM, optional GPU | Medium Ollama if healthy | Tile streaming | Light jobs only |
| `LINUX_WORKSTATION` | Primary server | Full Ollama + experts | Streaming + OCR + vectorize | Docker workers |
| `REMOTE_GPU_WORKER` | LUMI / GPU node | Large models | Batch analysis | DeepCell, Mesmer, StarDist |
| `CLOUD_TEACHER` | Optional | External API | N/A | Disabled for sensitive data |

Override host profile: `OMEIA_COMPUTE_HOST_PROFILE=LINUX_WORKSTATION`

## Routing rules

1. Can it run locally fast? → local
2. Else Linux workstation? → remote API / worker
3. Else Docker worker? → queue
4. Sensitive data → **never** cloud
5. No safe runtime → clear degraded message

## Feature flags

```bash
OMEIA_ADAPTIVE_COMPUTE=true          # master switch
OMEIA_AUTO_MODEL_DOWNGRADE=true      # smaller model when Ollama busy / RAM low
OMEIA_LOW_RESOURCE_MODE=false        # force LOW_END_LAPTOP behavior
OMEIA_REMOTE_GPU_WORKER_ENABLED=false
OMEIA_CLOUD_TEACHER_ENABLED=false    # never for private cohort data
OMEIA_HEAVY_JOBS_REQUIRE_QUEUE=true
```

## API

`GET /api/system/compute-status` — profile, capabilities, model tier, image mode, queue hints.

## Rollback

```bash
OMEIA_ADAPTIVE_COMPUTE=false
OMEIA_AUTO_MODEL_DOWNGRADE=false
```

Fixed model routing in `llm_client.py` continues unchanged.

## Linux validation

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/system/compute-status | jq .
python -c "from omeia.api.imaging_capabilities import probe_imaging_stack; import json; print(json.dumps(probe_imaging_stack(), indent=2))"
```
