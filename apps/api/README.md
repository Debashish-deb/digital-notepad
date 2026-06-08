# OMEIA API (FastAPI)

Backend package: `apps/api/src/app_skeleton/` (import namespace `app_skeleton.*`).

```bash
# From repo root (Linux)
export PYTHONPATH=apps/api/src
pip install -r apps/api/requirements.txt
uvicorn app_skeleton.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Or: `./scripts/dev/start_backend.sh` / `make start`.
