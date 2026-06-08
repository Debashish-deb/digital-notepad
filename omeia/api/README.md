# OMEIA FastAPI backend

REST API for the Farkki lab platform. The React UI is a **separate app** at `apps/web/`.

## Run (dev)

```bash
# From repo root
./scripts/dev/start_backend.sh
# or
./deploy/university-desktop/run_api_dev.sh
```

API: http://127.0.0.1:8000 — `GET /health`

## Configuration

- Copy `configs/.env.backend.example` → `configs/.env`
- Never put `VITE_*` variables on the server

## Docs

- [Frontend / backend tutorial](../../docs/FRONTEND_BACKEND_TUTORIAL.md)
- [Production deployment](../../docs/26_PRODUCTION_DEPLOYMENT.md)
- [Desktop install](../../deploy/university-desktop/README.md)
