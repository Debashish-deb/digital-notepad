# Repository layout

Linux is the authoritative runtime host. Mac is a dev/SSH thin client.

```
OMEIA-AI/
├── apps/
│   ├── api/src/app_skeleton/   # FastAPI (import: app_skeleton.*)
│   └── web/                    # React + Vite
├── infra/
│   ├── compose/                # docker-compose*.yml
│   ├── docker/                 # Dockerfiles
│   └── scripts/                # deploy, dev, ops, llm
├── config/env/                 # .env templates (symlink: configs/)
├── tests/                      # pytest suite
├── schemas/, sql/, data/       # shared artifacts at repo root
├── Makefile                    # make install | start | test | ready
├── start.sh, start_linux.sh    # thin wrappers → infra/scripts
└── docker-compose.yml          # symlink → infra/compose/
```

## Backward compatibility (one release)

- Root `scripts/` → `infra/scripts/`
- Root `configs/` → `config/env/`
- Root `app_skeleton/README.md` points to `apps/api/src/app_skeleton/`

## Python path

```bash
export PYTHONPATH=apps/api/src
```
