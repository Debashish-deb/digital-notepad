# University desktop backend (macOS & Linux)

Run the same FastAPI app on a **university lab machine** (production: Linux) or on a **Mac** for local/dev testing. Hostinger serves **React only**; the browser calls the API over HTTPS (prod) or `http://127.0.0.1:8000` (dev).

**Secrets:** `deploy/university-desktop/.env` or `configs/.env` (from `.env.desktop.example`) — never in Hostinger or `VITE_*`.

## Detect your OS

```bash
uname -s
# Linux  → production path: systemd, ufw, apt, Caddy/nginx
# Darwin → dev/test path: launchd OR ./run_api_dev.sh, optional brew caddy
```

| OS | Typical use | API bind | Process manager |
|----|-------------|----------|-----------------|
| **Linux** | Lab desktop production | `127.0.0.1:8000` behind :443 proxy | `omeia-api.service`, `omeia-ingest.timer`, `omeia-processor.service` |
| **macOS** | Local dev / parity testing | `127.0.0.1:8000` (default in `run_api_dev.sh`) | `./run_api_dev.sh` or `com.omeia.api.plist` (launchd) |

**Autonomous processor** (vault / digitalize / Supabase) runs **independently of Cursor IDE** — see `docs/28_AUTONOMOUS_PROCESSOR.md` and `./scripts/ops/autonomous_processor.sh`.

**Both platforms:** Python venv, same `omeia.api.main:app`, env from `.env.desktop.example`.

---

## Topology

```
Browser → Hostinger React (VITE_API_URL)
       → HTTPS → desktop (Caddy/nginx → 127.0.0.1:8000)   [Linux prod]
       → http://127.0.0.1:8000                             [Mac dev + Vite :5173]
       → Firebase token verify → Supabase permissions
       → DataCloud WebDAV / P-drive / local mounts
```

---

## Quick start — macOS (dev/test)

```bash
cd digital-notepad
python3 -m venv .venv && source .venv/bin/activate
pip install -r omeia/api/requirements.txt httpx pillow

cp deploy/university-desktop/.env.desktop.example configs/.env
# Edit: CORS_ORIGINS=http://localhost:5173,https://app.yourdomain.example
# PLATFORM_AUTH_DISABLED=true for local dev (default in example)

chmod +x deploy/university-desktop/run_api_dev.sh
./deploy/university-desktop/run_api_dev.sh
curl -s http://127.0.0.1:8000/health | jq .
```

Optional:

- **Auto-start:** `install_desktop_backend.sh` copies `launchd/com.omeia.api.plist` → `~/Library/LaunchAgents/`
- **TLS locally:** `brew install caddy` and adapt `Caddyfile.example`
- **Firewall:** bind `127.0.0.1` only for dev; macOS Application Firewall / `pf` are optional (see below)

---

## Quick start — Linux (production)

```bash
sudo mkdir -p /opt/omeia
sudo git clone <repo-url> /opt/omeia/digital-notepad
cd /opt/omeia/digital-notepad/deploy/university-desktop
chmod +x install_desktop_backend.sh run_api_dev.sh scheduled_ingest.sh
sudo ./install_desktop_backend.sh

sudo -u omeia nano /opt/omeia/deploy/university-desktop/.env
# CORS_ORIGINS=https://<hostinger-app-url>
# PLATFORM_AUTH_DISABLED=false, FIREBASE_SERVICE_ACCOUNT_PATH, DATACLOUD_*

sudo systemctl start omeia-api.service
sudo systemctl start omeia-ingest.timer
sudo cp omeia-processor.service /etc/systemd/system/
sudo systemctl enable --now omeia-processor.service
# TLS: Caddyfile.example or nginx-omeia.conf.example
# Firewall: ufw-notes.md (allow 443, not 8000)
```

---

## Scripts (both platforms)

| Script | Purpose |
|--------|---------|
| `run_api_dev.sh` | Load `.env`, run uvicorn (Mac/Linux) |
| `install_desktop_backend.sh` | `uname` branch: Linux → systemd; Darwin → launchd hints |
| `scheduled_ingest.sh` | Wrapper → `scripts/ops/scheduled_ingest.py` |

```bash
# Dev API (from repo root or any cwd — script resolves paths)
./deploy/university-desktop/run_api_dev.sh

# One-shot ingest
./deploy/university-desktop/scheduled_ingest.sh
```

Env load order (same as Python ingest): `configs/.env` → `deploy/university-desktop/.env` → process environment.

`run_api_dev.sh` variables:

| Variable | Default | Notes |
|----------|---------|-------|
| `OMEIA_BIND_HOST` | `127.0.0.1` on Darwin, `0.0.0.0` on Linux | Override either OS |
| `OMEIA_BIND_PORT` | `8000` | |
| `OMEIA_VENV` | repo `.venv` or `/opt/omeia/venv` if present | |

---

## Environment & mount paths

Copy `.env.desktop.example` to `configs/.env` (dev) or `/opt/omeia/deploy/university-desktop/.env` (Linux prod).

**Linux** — SMB/GVFS and `/mnt` mounts:

```bash
LAB_STORAGE_ROOT=/run/user/1000/gvfs/smb-share:server=...
PDRIVE_MOUNT_PATH=/mnt/pdrive
```

**macOS** — `/Volumes` mounts:

```bash
# LAB_STORAGE_ROOT=/Volumes/farkki_digital_notebook
# PDRIVE_MOUNT_PATH=/Volumes/Pdrive
```

**Mac local dev (example defaults in template):**

```bash
CORS_ORIGINS=http://localhost:5173,https://app.yourdomain.example
PLATFORM_AUTH_DISABLED=true
```

**Linux production auth:**

```bash
CORS_ORIGINS=https://app.yourdomain.example
PLATFORM_AUTH_DISABLED=false
FIREBASE_SERVICE_ACCOUNT_PATH=/opt/omeia/secrets/firebase-adminsdk.json
```

Auth/CORS behavior is unchanged in code; only env differs per environment.

---

## Linux: systemd, firewall, packages

| Unit | Role |
|------|------|
| `omeia-api.service` | uvicorn on **127.0.0.1:8000** |
| `omeia-ingest.service` | One-shot `scheduled_ingest.sh` / `.py` |
| `omeia-ingest.timer` | Daily ingest |

```bash
sudo cp deploy/university-desktop/omeia-api.service /etc/systemd/system/
sudo cp deploy/university-desktop/omeia-ingest.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now omeia-api.service omeia-ingest.timer
```

- **ufw:** `ufw-notes.md`
- **apt:** `python3-venv`, `caddy` or `nginx` per site policy
- **TLS:** `Caddyfile.example` or `nginx-omeia.conf.example`

---

## macOS: launchd & firewall

**launchd (optional auto-start):**

```bash
./deploy/university-desktop/install_desktop_backend.sh
# Copies launchd/com.omeia.api.plist → ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.omeia.api.plist
launchctl start com.omeia.api
```

Edit plist `EnvironmentVariables` and `ProgramArguments` paths if the repo is not under `$HOME/digital-notepad`.

**Firewall notes:**

- Prefer **`127.0.0.1:8000`** for dev so the API is not LAN-exposed.
- macOS Application Firewall: allow Terminal/Python if you bind `0.0.0.0`.
- **`pf`** rules are optional; not required for localhost-only dev.

---

## Firebase on protected routes

When `PLATFORM_AUTH_DISABLED=false`:

- `/api/storage/*`, `/api/vault/*`, `/api/digitalize/*`, `/api/supabase/*`
- Downloads and asset URLs as documented in `docs/27_UNIVERSITY_DESKTOP_BACKEND.md`

Public: `/health`, `/api/auth/config`, `/api/platform/connectors`.

---

## Hostinger frontend

```bash
cd omeia/ui/react_frontend
# .env.production: VITE_API_URL=https://<desktop-public-host>
npm ci && npm run build
```

Desktop `.env` must list the exact Hostinger origin in `CORS_ORIGINS`.

---

## Scheduled ingest

`scripts/ops/scheduled_ingest.py` — read-only scans, optional Supabase sync, thumbnails via `thumbnail_service` (Path-based; works on macOS and Linux).

```bash
./deploy/university-desktop/scheduled_ingest.sh
# Linux systemd:
sudo -u omeia /opt/omeia/venv/bin/python /opt/omeia/digital-notepad/scripts/ops/scheduled_ingest.py
```

---

## Verification

```bash
curl -s http://127.0.0.1:8000/health | jq .
curl -s http://127.0.0.1:8000/api/auth/config | jq .
# Mac dev: auth_disabled: true when PLATFORM_AUTH_DISABLED=true
```

---

## NEEDS_USER_DECISION

| Item | Notes |
|------|--------|
| Public API hostname | DNS or tunnel to **Linux** desktop |
| TLS | Caddy vs nginx vs university proxy |
| Hostinger URL | `CORS_ORIGINS` + Firebase authorized domains |
| Mac vs Linux role | Mac = dev/test; Linux = production |

See: `docs/27_UNIVERSITY_DESKTOP_BACKEND.md`, `docs/26_PRODUCTION_DEPLOYMENT.md`, `configs/DEPLOYMENT_ENV.md`.
