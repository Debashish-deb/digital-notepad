# Your OMEIA setup (canonical — do not change workflow each session)

**Configured 2026-06-07/08.** Tailscale mesh is live. Linux is the permanent host.

## Fixed facts

| Item | Value |
|------|--------|
| Linux host | `<linux-hostname>` |
| Linux Tailscale IP | `100.80.231.55` |
| Linux repo | `~/data4TB/digital-notepad` |
| Linux data | `~/data4TB/OMEIA-database` |
| Mac `configs/.env` | `TAILSCALE_LINUX_IP=100.80.231.55` |

## How you use the app (every day)

1. **Linux** keeps running: `./scripts/start_linux.sh` (or already up)
2. **Mac browser** opens: **http://100.80.231.55:5173**
3. **No Mac API, no Mac Docker** — Tailscale carries HTTP only

Ollama + Qdrant reach Linux via Tailscale HTTP + `OLLAMA_INTERNAL_TOKEN` (already working).

## Code updates (no Mac SSH password needed)

**Mac** — push only:

```bash
cd /path/to/OMEIA-AI
./scripts/deploy/mac_push_to_linux.sh --git-only
```

**Linux** (terminal you already have open on the workstation):

```bash
cd ~/data4TB/digital-notepad
git pull
./scripts/start_linux.sh
```

That is the normal loop. Do **not** rely on `ssh labuser@100.80.231.55` from Mac unless you explicitly set up SSH keys or Tailscale SSH.

## Heavy data (OMEIA-database)

Tailscale does **not** replace SSH for `rsync`. Options:

1. **Already on Linux** — check: `ls ~/data4TB/OMEIA-database/SOCIAL | head`
2. **Linux terminal** — copy from USB to `~/data4TB/OMEIA-database`
3. **Tailscale file send** (no SSH password):

```bash
# Mac
tailscale file cp -r /path/to/OMEIA-database labuser@<linux-hostname>:

# Linux
tailscale file get .
mv OMEIA-database ~/data4TB/
```

4. **SSH keys** (one-time): only if you want `mac_push_to_linux.sh` rsync from Mac

## What Tailscale is / is not

| Tailscale handles | Does NOT handle |
|-------------------|-----------------|
| Browser → Linux UI `:5173` | Linux user password for `ssh` |
| Mac API → Linux Ollama `:11434` | Automatic `rsync` without SSH keys |
| Mac → Linux Qdrant `:6333` | Postgres from Mac (not needed — use Linux UI) |

## If images fail in the UI

Files must exist on **Linux disk** at `DATABASE_ROOT`, not on Mac. See `docs/LINUX_MEDIA_AND_DATA_PATHS.md`.

## Sync lab files Mac → Linux (previews / thumbnails)

**Run on the Mac**, not on Linux. Linux only has metadata until you rsync binaries.

```bash
# Mac Terminal:
cd ~/Downloads/OMEIA-AI   # or your clone path
export LINUX_SSH=labuser@100.80.231.55
export MAC_DATABASE_ROOT=/path/to/OMEIA-database
./scripts/deploy/mac_push_to_linux.sh --data-only
```

First time: set up passwordless SSH so rsync does not stop mid-transfer:

```bash
ssh-copy-id labuser@100.80.231.55
```

Expect a long run (full `SOCIAL & MISCELLANEOUS`, `WET_LAB`, etc.). After sync, on Linux:

```bash
ls ~/data4TB/OMEIA-database
./scripts/start_linux.sh
```

## Node.js on Linux (Vite 8)

Cubbli ships Node 20.11 — **too old**. Upgrade once with nvm:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.nvm/nvm.sh
nvm install 22
nvm use 22
node -v   # expect v22.x
```

Then `npm install` in `app_skeleton/ui/react_frontend` and `./scripts/start_linux.sh`.

## One-shot Linux bootstrap (after git pull)

```bash
cd ~/data4TB/digital-notepad
./scripts/deploy/linux_bootstrap_all.sh
./scripts/start_linux.sh
```
