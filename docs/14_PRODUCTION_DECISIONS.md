# 14 — Production decisions (user-confirmed)

**Status:** Dev twin fully usable. Production connectors **stubbed** until credentials are supplied via `.env` (never committed).

## Agreed policies (2026-06-03)

| Topic | Decision |
|-------|----------|
| **Platform admins** | `anniina.farkkila@helsinki.fi`, `debashish.deb@helsinki.fi`, `joonas.jukonen@helsinki.fi` |
| **Allowlist source** | `app_skeleton/data/lab_personnel_roster.json` (from lab-newspaper-site); inferred emails use `firstname.lastname@helsinki.fi` (ä→a, ö→o, å→a) |
| **Research Materials** | Under **Projects** (`database/projects/RESEARCH MATERIALS/`); Overview nav is a lens only |
| **Personnel roster** | Public lab site + `Overview/PERSONNEL/` on disk; treat as **tentative** until HR-confirmed |
| **Dated exports `*-20260602T*`** | Do not delete; index metadata; mark possible superseded; human review |
| **Clinical / sensitive** | No external AI; no vectorize until reviewed; metadata-first; `restricted_or_clinical_review` |
| **Firebase auth** | **Email/Password only** — project `farkki-digital-notebook` (570069536455). Web app **OMEIA.AI** `1:570069536455:web:4c4623a81262e6c4eef8e2`. **No Google Sign-In.** |
| **Firebase console** | Owner login `farkkilalab@gmail.com` (password **never** stored in repo; enter locally in Console or CLI when connecting) |
| **Platform users** | University `@helsinki.fi` allowlist — separate from Firebase console Gmail |
| **Supabase** | **User will provide credentials later** — metadata + optional small-file Storage |
| **Cloudflare R2** | **Removed** from architecture (deprecated stub only); previews via Supabase Storage or backend |

## Still deferred (credentials or mapping)

| Blocker | Action when ready |
|---------|-------------------|
| DataCloud path mapping | Confirm local `database/**` → `/farkkila/LAB-ASSISTANT-PLATFORM/**` table |
| Digital Pathology admin email | Second admin besides lab PI/IT/coordinator if required |
| Supabase | Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` |
| Firebase | Enable **Email/Password** in console; set `FIREBASE_WEB_API_KEY`, `FIREBASE_WEB_APP_ID`, `FIREBASE_SERVICE_ACCOUNT_PATH`, `PLATFORM_AUTH_DISABLED=false` |
| DataCloud WebDAV | Set `DATACLOUD_WEBDAV_BASE_URL`, `DATACLOUD_USERNAME`, `DATACLOUD_APP_PASSWORD` |
| P-drive mount | Set `PDRIVE_ENABLED=true`, `PDRIVE_MOUNT_PATH` when share is mounted |

## Dev vs production

| Service | Dev now | Production when env filled |
|---------|---------|----------------------------|
| Database | `POSTGRES_CONN` (local Docker) | `SUPABASE_*` hosted |
| Auth | `PLATFORM_AUTH_DISABLED=true` | Firebase verify + allowlist |
| Object previews | None / local API | Supabase Storage (small files) or backend-generated |
| Files | `database/` mirror | DataCloud WebDAV (+ optional P-drive) |

## API checks (no secrets)

- `GET /health` → `connectors` object
- `GET /api/platform/connectors` → Firebase / Supabase / DataCloud / P-drive flags

## Production deployment

Full topology, request flow, env matrix per host, and Hostinger build steps: **`docs/26_PRODUCTION_DEPLOYMENT.md`**.

Copy-paste env checklist: **`configs/DEPLOYMENT_ENV.md`**.

Supabase document sync on free tier: **`docs/25_SUPABASE_SYNC_POLICY.md`**.

## Reference files

- `docs/26_PRODUCTION_DEPLOYMENT.md` — Hostinger + API + Supabase + Firebase + DataCloud split
- `configs/DEPLOYMENT_ENV.md` — production env checklist
- `docs/15_STORAGE_MASTER_PLAN.md` — workstreams and deliverable checklist
- `docs/16–23` — connector design, ingestion, validation, registry, safety, workers
- `configs/.env.example` — all variable names
- `configs/FIREBASE_WEB_SETUP.md` — full Console SDK snippet + what OMEIA uses
- `app_skeleton/api/firebase_app.py` — Firebase Admin init
- `app_skeleton/ui/react_frontend/src/config/firebase.js` — web config + optional Analytics
- `app_skeleton/api/connector_status.py` — readiness summary
- `app_skeleton/data/lab_personnel_roster.json` — members + admin emails
