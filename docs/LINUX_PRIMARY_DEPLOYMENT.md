# Linux-primary deployment (permanent target)

OMEIA runs **entirely on the Linux workstation**. Mac is a **browser client only** (Tailscale URL).

| Component | Host |
|-----------|------|
| Git repo | `~/data4TB/digital-notepad` |
| Lab files (`OMEIA-database`) | `~/data4TB/OMEIA-database` |
| Docker (Postgres, Qdrant, Ollama) | Linux |
| FastAPI + Vite | Linux |
| Biomedical / imaging Docker | Linux |
| Mac | Chrome → `http://100.x.x.x:5173` |

## Your Tailscale setup (already done)

- Linux: `dx9-3049-11090` @ **`100.80.231.55`**
- Browser: **http://100.80.231.55:5173**
- Mac `TAILSCALE_LINUX_IP=100.80.231.55` in `configs/.env`

See **`docs/YOUR_SETUP.md`** for the single canonical workflow (avoid re-asking each session).

## Code push (normal — no SSH from Mac)

**Mac:**

```bash
cd /Users/debashishdeb/Downloads/OMEIA-AI
./scripts/deploy/mac_push_to_linux.sh --git-only
```

**Linux** (workstation terminal):

```bash
cd ~/data4TB/digital-notepad && git pull && ./scripts/start_linux.sh
```

## Heavy data (one-time)

Tailscale HTTP does not rsync files. Use **Linux terminal**, USB, or:

```bash
# Mac
tailscale file cp -r /Users/debashishdeb/Downloads/OMEIA-database debdeba@dx9-3049-11090:
```

Optional: `mac_push_to_linux.sh` rsync only works with SSH keys or Tailscale SSH — not the Linux login password unless you know it.

## One-time: Linux full bootstrap

On **Linux**:

```bash
cd ~/data4TB/digital-notepad
chmod +x scripts/deploy/linux_bootstrap_all.sh scripts/deploy/mac_push_to_linux.sh
./scripts/deploy/linux_bootstrap_all.sh
# Optional heavy biomedical containers:
./scripts/deploy/linux_bootstrap_all.sh --with-biomodels
```

## Daily workflow

| Machine | Action |
|---------|--------|
| **Mac** (code changes) | edit → `mac_push_to_linux.sh --code-only` |
| **Linux** | `git pull && ./scripts/start_linux.sh` |
| **Any browser** | `http://<linux-tailscale-ip>:5173` |

## Mac `.env` (browser-only client)

```env
TAILSCALE_LINUX_IP=100.80.231.55
DOCKER_LOCAL=false
# Do NOT run ./scripts/start_mac.sh for full app — use Linux URL in browser.
```

Copy Firebase/Supabase secrets from Mac `configs/.env` to Linux `configs/.env` once (never commit).

## Verify

```bash
# Linux
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
find ~/data4TB/OMEIA-database -name '*.jpg' | head -3
docker compose ps
```

## Related docs

- `docs/LINUX_MEDIA_AND_DATA_PATHS.md` — preview troubleshooting  
- `docs/TAILSCALE_SETUP.md` — mesh networking  
- `configs/linux-workstation.env.template` — canonical Linux env template  
