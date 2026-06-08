# Repository layout

Linux is the authoritative runtime host. Mac is a dev/SSH thin client.

```
OMEIA-AI/
├── omeia/                      # FastAPI package (import: omeia.*)
│   ├── api/                    # HTTP API, routers, services
│   ├── digitalization/         # Document ingestion pipeline
│   ├── pipelines/              # Image processing pipelines
│   ├── security/               # Auth, permissions, audit
│   └── storage/                # Datacloud, SMB, ingestion adapters
├── web/                        # React + Vite frontend
├── infra/
│   ├── compose/                # docker-compose*.yml
│   ├── docker/                 # Dockerfiles
│   └── scripts/                # deploy, dev, ops, llm
├── config/env/                 # .env templates (symlink: configs/)
├── tests/                      # pytest suite
├── schemas/, sql/, data/       # shared artifacts at repo root
├── synthetic_data/             # synthetic fixtures
├── deploy/                     # university-desktop installers
├── Makefile                    # make install | start | test | ready
├── start.sh, start_linux.sh    # thin wrappers → infra/scripts
└── docker-compose.yml          # symlink → infra/compose/
```

## Backward compatibility (one release)

- Root `scripts/` → `infra/scripts/`
- Root `configs/` → `config/env/`

## Python path

```bash
export PYTHONPATH=.
python -c "from omeia.api.main import app; print('ok')"
```
