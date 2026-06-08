# Linux media previews and data paths

When you open the UI at `http://<linux-tailscale-ip>:5173`, the browser loads the page from Linux Vite but **files must exist on the Linux disk** at `DATABASE_ROOT` and `PROJECTS_ROOT`.

## Why Mac worked but Linux did not

| Layer | Mac (local) | Linux (remote UI) |
|-------|-------------|-------------------|
| UI | `localhost:5173` | `100.x.x.x:5173` |
| API | `localhost:8000` | same Linux host `:8000` (Vite proxy) |
| Ollama / Qdrant | local or Tailscale | Linux Docker |
| **Media files** | `../OMEIA-database` on Mac disk | Must be `~/data4TB/OMEIA-database` on Linux |

Postgres metadata (INDEXED badge, excellent grade) can exist **without** the binary file on disk. Previews fail with **"Could not load image"** when the path is missing.

## Required Linux `configs/.env`

```env
DATABASE_ROOT=/home/debdeba/data4TB/OMEIA-database
PROJECTS_ROOT=/home/debdeba/data4TB/OMEIA-database/projects
# Optional SMB lab notebook mount:
# LAB_STORAGE_ROOT=/mnt/lab-notebook
```

Restart after changing paths:

```bash
./scripts/start_linux.sh
```

## Verify a file exists

For asset `20220617_170839.jpg` in Social:

```bash
find ~/data4TB/OMEIA-database -name '20220617_170839.jpg' 2>/dev/null | head -3
curl -sI "http://127.0.0.1:8000/database-static/SOCIAL/.../20220617_170839.jpg" | head -5
```

`HTTP/1.1 200` = API can serve the file. `404` = sync or fix `DATABASE_ROOT`.

## Sync data from Mac (one-time)

If the canonical lab tree lives on Mac:

```bash
rsync -av --progress /path/to/Mac/OMEIA-database/ debdeba@100.80.231.55:~/data4TB/OMEIA-database/
```

## Integrated software (biomedical, imaging)

These run as **Docker on Linux** (`127.0.0.1:8100` etc.). The UI reaches them via `/api/biomedical-models/*` on the Linux API — works when browsing the Linux URL. They do **not** run on the Mac when using thin-client mode.

## Mac thin client

`./scripts/start_mac.sh` only tunnels Ollama + Qdrant. For full previews on Mac you still need either:

1. Browse Linux UI directly (`http://100.80.231.55:5173`), or  
2. Remote `POSTGRES_CONN` + rsync/mount `DATABASE_ROOT` on Mac.
