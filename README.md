# OMEIA — Clinical & Spatial Biology Research Platform

FastAPI backend + React SPA for lab knowledge, search, imaging, and AI assistants. **Linux is the primary runtime host**; Mac clients use Tailscale to the Linux workstation.

## Linux quick start

```bash
cd ~/data4TB/digital-notepad   # or your clone path
git pull
make install
make start
make ready
# Browser: http://$(tailscale ip -4):5173
```

Equivalent: `./start_linux.sh` (Docker + API :8000 + Vite :5173).

| App | Path | Port |
|-----|------|------|
| Frontend | `apps/web/` | **5173** (dev) |
| Backend | `apps/api/src/app_skeleton/` | **8000** |
| Compose | `infra/compose/docker-compose.yml` | Postgres, Qdrant, Ollama |

```bash
make install    # pip + npm deps
make test       # pytest
make stop       # stop local stack
```

## Layout

See [docs/architecture/REPOSITORY_LAYOUT.md](docs/architecture/REPOSITORY_LAYOUT.md).

Legacy path stubs: root `scripts/` → `infra/scripts/`, `configs/` → `config/env/`, `app_skeleton/README.md` → API package.

## Mac thin client

Point `TAILSCALE_LINUX_IP` at the Linux host and run `./scripts/dev/start_mac_thin_client.sh` — API calls go to Linux; no local Docker required.

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/OMEIA_INFORMATION_FLOW.md](docs/OMEIA_INFORMATION_FLOW.md)
- [docs/FRONTEND_BACKEND_TUTORIAL.md](docs/FRONTEND_BACKEND_TUTORIAL.md)
