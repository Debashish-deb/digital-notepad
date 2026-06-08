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

## One-time: Mac → Linux pack & push

On **Mac** (repo + heavy data):

```bash
cd /Users/debashishdeb/Downloads/OMEIA-AI
export LINUX_SSH=debdeba@100.80.231.55   # Linux Tailscale IP
./scripts/deploy/mac_push_to_linux.sh
```

This will:

1. `git push` from Mac  
2. `git pull` on Linux  
3. `rsync` `OMEIA-database/` → Linux `~/data4TB/OMEIA-database/`  
4. `rsync` `labMember/` avatars if present  

Options:

```bash
./scripts/deploy/mac_push_to_linux.sh --code-only   # git only, no rsync
./scripts/deploy/mac_push_to_linux.sh --data-only   # rsync only
./scripts/deploy/mac_push_to_linux.sh --dry-run
```

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
