# OMEIA React frontend (Vite)

This is the **frontend application**. The API lives separately at `omeia/api/` (port 8000).

**Full architecture guide:** [docs/FRONTEND_BACKEND_TUTORIAL.md](../../../docs/FRONTEND_BACKEND_TUTORIAL.md)

## Quick start (frontend only)

```bash
# From repo root — backend must already be running
./scripts/dev/start_frontend.sh
```

## Local full-stack development

### 1. PostgreSQL (local)

Use an existing Postgres instance or Docker:

```bash
docker run -d --name omeia-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=omeia -p 5432:5432 postgres:16
```

Point `POSTGRES_CONN` / `DATABASE_URL` in `configs/.env` at that instance (see repo `configs/DEPLOYMENT_ENV.md`).

### 2. Backend API

From the repo root (`farkki_ai_platform_blueprint`):

```bash
# configs/.env — set POSTGRES_CONN, optional DATABASE_ROOT, LAB_STORAGE_ROOT
export PLATFORM_AUTH_DISABLED=true   # skip Firebase on protected routes in dev
./deploy/university-desktop/run_api_dev.sh
```

API listens at **http://127.0.0.1:8000** (`GET /health` should return `"status": "ok"` when DB is up).

### 3. Frontend

```bash
cd apps/web
cp .env.local.example .env.local
npm ci
npm run dev
```

`.env.local` (from `.env.local.example`):

```bash
VITE_API_URL=http://127.0.0.1:8000
```

Optional Firebase (only if testing real auth — not required when `PLATFORM_AUTH_DISABLED=true`):

- `VITE_FIREBASE_API_KEY` — same as `FIREBASE_WEB_API_KEY` in `configs/.env`
- Other `VITE_FIREBASE_*` — see `configs/FIREBASE_WEB_SETUP.md`

Vite proxies `/api`, `/stats`, `/projects`, etc. to port 8000 when using relative URLs; with `VITE_API_URL` set, the shared client in `src/api/client.js` calls the API host directly.

### 4. Verify

- Sidebar shows API **Connected** when `/health` succeeds.
- **Overview / Orders / Wet-lab** — section screens load extracted twins from local processed JSON (not Supabase).
- **Data & Storage** — vault summary, connectors, digitalization, Supabase sync (dry run).
- **Administration** — health, connectors, ingestion jobs, Firebase panel.
- **Knowledge search** — `/api/search` and hybrid-search.

Lab section API (reads `omeia/data/processed_projects/lab__*.json`):

```bash
curl -s http://127.0.0.1:8000/api/lab/sections | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/lab/section/wet_lab_files | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['metrics']['extracted_document_count'])"
# Expect: 461
curl -s "http://127.0.0.1:8000/api/lab/section/wet_lab_files/documents?q=Sectioning&limit=5"
```

```bash
npm run build
```

## Production build (Hostinger)

1. Create `.env.production` with at least:

   ```bash
   VITE_API_URL=https://api.yourdomain.example
   VITE_FIREBASE_API_KEY=...
   # remaining VITE_FIREBASE_* — configs/DEPLOYMENT_ENV.md
   ```

2. Build and upload:

   ```bash
   npm run build
   ```

3. Upload **contents** of `dist/` to the app subdomain document root.

4. Enable SPA fallback (`index.html` for client routes) — `.htaccess` example in `docs/26_PRODUCTION_DEPLOYMENT.md`.

**Do not** put `DATACLOUD_*`, Supabase service role, or database passwords in any `VITE_*` file.

## Docs

| Topic | File |
|-------|------|
| Full production topology | `docs/26_PRODUCTION_DEPLOYMENT.md` |
| Env checklist | `configs/DEPLOYMENT_ENV.md` |
| Firebase web config | `configs/FIREBASE_WEB_SETUP.md` |
