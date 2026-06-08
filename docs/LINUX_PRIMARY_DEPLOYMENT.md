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

- Linux workstation @ **`100.x.x.x`** (Tailscale IP)
- Browser: **http://100.80.231.55:5173**
- Mac `TAILSCALE_LINUX_IP=100.80.231.55` in `configs/.env`

See **`docs/YOUR_SETUP.md`** for the single canonical workflow (avoid re-asking each session).

## Code push (normal — no SSH from Mac)

**Mac:**

```bash
cd /path/to/OMEIA-AI
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
tailscale file cp -r /path/to/OMEIA-database labuser@<linux-hostname>:
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

## Auto-sync (ping + git)

**Linux** — background pull every 90s when Mac has pushed:

```bash
cd ~/data4TB/digital-notepad
chmod +x scripts/deploy/auto_sync_daemon.sh
./scripts/deploy/auto_sync_daemon.sh
# Or enable on login:
cp scripts/deploy/omeia-auto-sync.service ~/.config/systemd/user/
systemctl --user enable --now omeia-auto-sync.service
```

**Mac** — push when Linux answers ping:

```bash
# configs/.env: TAILSCALE_LINUX_IP=100.x.x.x  LINUX_SSH=user@host
./scripts/deploy/auto_sync_daemon.sh --mac-push
```

Status log: `omeia/data/auto_sync_last_run.json`

## Daily workflow

| Machine | Action |
|---------|--------|
| **Mac** (code changes) | edit → `mac_push_to_linux.sh --code-only` or auto-sync `--mac-push` |
| **Linux** | auto-sync daemon, or `git pull && ./scripts/start_linux.sh` |
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
