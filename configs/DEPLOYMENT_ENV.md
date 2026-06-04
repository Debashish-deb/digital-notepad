# Production deployment — environment checklist

Copy values into the right host **before** go-live. Full topology: `docs/26_PRODUCTION_DEPLOYMENT.md`, desktop guide: `docs/27_UNIVERSITY_DESKTOP_BACKEND.md`.

**Rules:** No Cloudflare R2 required. Frontend never gets WebDAV creds, Supabase service role, or database password.

---

## 1. Hostinger — React build (`.env.production` in `react_frontend/`)

Create `app_skeleton/ui/react_frontend/.env.production` (gitignored). Build with `npm run build`; upload `dist/` to the app subdomain.

```bash
# --- API (required in production) ---
VITE_API_URL=https://api.yourdomain.example

# --- Firebase web (public; Email/Password only) ---
VITE_FIREBASE_API_KEY=<Firebase Console → Project settings → Web API key>
VITE_FIREBASE_AUTH_DOMAIN=farkki-digital-notebook.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=farkki-digital-notebook
VITE_FIREBASE_STORAGE_BUCKET=farkki-digital-notebook.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=570069536455
VITE_FIREBASE_APP_ID=1:570069536455:web:4c4623a81262e6c4eef8e2
VITE_FIREBASE_MEASUREMENT_ID=G-24JLFQYRTG
```

**Cross-check:** `configs/FIREBASE_WEB_SETUP.md`, `app_skeleton/ui/react_frontend/README.md`.

**Never add to Hostinger / Vite:**

- `DATACLOUD_*`
- `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_PASSWORD`, `SUPABASE_ANON_KEY` (unless you deliberately add a Supabase browser client later)
- `FIREBASE_SERVICE_ACCOUNT_PATH` / Admin SDK JSON
- `POSTGRES_CONN`, `PLATFORM_AUTH_DISABLED`

---

## 2. University desktop — FastAPI (`deploy/university-desktop/.env`)

Copy `deploy/university-desktop/.env.desktop.example` → `/opt/omeia/deploy/university-desktop/.env` (see `install_desktop_backend.sh`).

```bash
APP_ENV=production
LOG_LEVEL=INFO

# Must match your Hostinger app URL (comma-separated)
CORS_ORIGINS=https://app.yourdomain.example

# --- Auth (production) ---
PLATFORM_AUTH_DISABLED=false
FIREBASE_PROJECT_ID=farkki-digital-notebook
FIREBASE_AUTH_DOMAIN=farkki-digital-notebook.firebaseapp.com
FIREBASE_WEB_API_KEY=<same as VITE_FIREBASE_API_KEY>
FIREBASE_WEB_APP_ID=1:570069536455:web:4c4623a81262e6c4eef8e2
FIREBASE_SERVICE_ACCOUNT_PATH=/opt/omeia/secrets/firebase-adminsdk.json
PLATFORM_ADMIN_EMAILS=anniina.farkkila@helsinki.fi,debashish.deb@helsinki.fi,joonas.jukonen@helsinki.fi

# --- Supabase (backend only) ---
SUPABASE_URL=https://ccpvupyiqxubcupvtrtp.supabase.co
SUPABASE_PROJECT_REF=ccpvupyiqxubcupvtrtp
SUPABASE_POOLER_HOST=aws-1-eu-central-1.pooler.supabase.com
SUPABASE_POOLER_PORT=6543
SUPABASE_ANON_KEY=<anon JWT>
SUPABASE_SERVICE_ROLE_KEY=<service_role JWT — server only>
SUPABASE_DB_PASSWORD=<database password — server only>

# Document sync — see docs/25_SUPABASE_SYNC_POLICY.md
SUPABASE_SYNC_ENABLED=false
SUPABASE_MAX_TEXT_BYTES=50000
SUPABASE_SYNC_BATCH_SIZE=100
SUPABASE_SKIP_IMAGE_SYNC=true
SUPABASE_MAX_DB_MB=450

# --- DataCloud WebDAV (backend only) ---
DATACLOUD_WEBDAV_BASE_URL=https://datacloud.helsinki.fi/remote.php/dav/files/<user>%40helsinki.fi
DATACLOUD_ROOT=/farkkila/LAB-ASSISTANT-PLATFORM
DATACLOUD_USERNAME=
DATACLOUD_APP_PASSWORD=

# --- P-drive / lab paths ---
PDRIVE_ENABLED=false
PDRIVE_MOUNT_PATH=
LAB_STORAGE_ROOT=
PREVIEW_CACHE_DIR=

# --- Repo root on desktop ---
OMEIA_REPO_ROOT=/opt/omeia/digital-notepad
```

**No `VITE_*` on the desktop.**

---

## 3. Firebase Console (not a `.env` file)

- [ ] Authentication → Sign-in method → **Email/Password** enabled; Google disabled
- [ ] Authentication → Settings → Authorized domains → add `app.yourdomain.example`
- [ ] Download service account JSON → `/opt/omeia/secrets/` on desktop only

---

## 4. Supabase Dashboard

- [ ] Database password → `SUPABASE_DB_PASSWORD` on desktop only
- [ ] API keys → anon + service role on desktop; do not embed service role in frontend
- [ ] After migrations: optional sync per `docs/25_SUPABASE_SYNC_POLICY.md`

---

## 5. DataCloud

- [ ] App password created (not university password)
- [ ] Folder `/farkkila/LAB-ASSISTANT-PLATFORM` exists and is shared
- [ ] See `configs/DATACLOUD_WEBDAV_SETUP.md`

---

## 6. systemd + TLS (desktop)

- [ ] `omeia-api.service` — `127.0.0.1:8000`
- [ ] Caddy or nginx — HTTPS to public hostname
- [ ] `ufw` — allow 443, deny public 8000 (`deploy/university-desktop/ufw-notes.md`)
- [ ] `omeia-ingest.timer` — daily `scheduled_ingest.py`

---

## 7. Post-deploy verification

```bash
curl -s http://127.0.0.1:8000/health | jq .
curl -s https://api.yourdomain.example/api/platform/connectors | jq .
```

Expect `auth_disabled: false` when `PLATFORM_AUTH_DISABLED=false`.

Protected route smoke test (no token → 401):

```bash
curl -s -o /dev/null -w "%{http_code}" https://api.yourdomain.example/api/storage/roots
# Expect 401
```

---

## NEEDS_USER_DECISION

| Item | You choose |
|------|------------|
| App subdomain | e.g. `https://app.yourdomain.example` |
| API public hostname | e.g. `https://api.yourdomain.example` — DNS or tunnel to desktop |
| TLS | Caddy automatic vs nginx + certbot vs university reverse proxy |
| Hostinger path | Subdomain document root vs addon domain folder |
| Network to desktop | Public 443, VPN-only, or IT-approved tunnel |
| When to enable sync | `SUPABASE_SYNC_ENABLED=true` only after dry-run |
