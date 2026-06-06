# Portable deployment — Mac now, Linux desktop later

Same git repo + `configs/.env` + `configs/secrets/` moves between machines.

## Mac thin client (today)

| Component | Where |
|-----------|--------|
| UI + API | Mac (`./scripts/start_portable.sh`) |
| Ollama + models | Linux Docker (`digital-notepad`) |
| Postgres | Supabase cloud (no local Docker) |
| Link Mac→Linux | **Tailscale** (`100.x.x.x`) |

### Mac one-time

```bash
./scripts/setup_mac_portable.sh
sudo brew services start tailscale
sudo tailscale up
```

### Linux one-time

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up   # same Tailscale account
tailscale ip -4     # e.g. 100.64.0.12
```

### Mac `configs/.env`

```env
OMEIA_DEPLOYMENT_PROFILE=mac_thin_client
DOCKER_LOCAL=false
TAILSCALE_LINUX_IP=100.64.0.12
OLLAMA_INTERNAL_TOKEN=<same as Linux>
LLM_PROVIDER=ollama
LLM_FALLBACK_PROVIDERS=ollama,gemini,mock
```

`scripts/portable_apply_env.sh` sets `OLLAMA_BASE_URL` and `QDRANT_URL` from `TAILSCALE_LINUX_IP`.

### Daily start (Mac)

```bash
./scripts/start_portable.sh
```

Open http://localhost:5173

---

## Move permanently to Linux desktop

1. **Copy to Linux** (or `git clone` + copy secrets):
   - `configs/.env`
   - `configs/secrets/` (Firebase service account)
   - `OMEIA-database/` (or set `DATABASE_ROOT` on Linux)

2. **Edit `configs/.env` on Linux:**

```env
OMEIA_DEPLOYMENT_PROFILE=linux_desktop
DOCKER_LOCAL=true
TAILSCALE_LINUX_IP=
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
QDRANT_URL=http://127.0.0.1:6333
DATABASE_ROOT=/home/debdeba/data4TB/OMEIA-database
FIREBASE_SERVICE_ACCOUNT_PATH=/home/debdeba/data4TB/digital-notepad/configs/secrets/firebase-adminsdk.json
```

3. **Start stack on Linux:**

```bash
cd ~/data4TB/digital-notepad
scripts/start_linux_docker_stack.sh
./scripts/start_portable.sh
```

4. **Browser:** `http://localhost:5173` on Linux (or SSH port-forward if remote).

5. **Mac:** stop using it or keep as thin client — no code changes required.

---

## Files to never commit

- `configs/.env`
- `configs/secrets/*`

## Files that travel with the repo

- `scripts/start_portable.sh`
- `scripts/portable_apply_env.sh`
- `configs/.env.example`
- `docs/TAILSCALE_SETUP.md`
