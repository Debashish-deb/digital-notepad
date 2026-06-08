# OMEIA-AI repository structure

High-level layout of the OMEIA / Farkki research platform monorepo.

```
OMEIA-AI/
├── start.sh                 # Launch API + React dev stack
├── docker-compose.yml       # Local Postgres, Qdrant, Ollama (when DOCKER_LOCAL=true)
├── README.md
│
├── omeia/            # Application code
│   ├── api/                 # FastAPI backend (port 8000)
│   ├── ui/react_frontend/   # React SPA (port 5173)
│   ├── ui/streamlit_app.py  # Legacy Streamlit dashboard
│   ├── data/                # Runtime JSON, processor state, logs
│   ├── digitalization/      # Digitalization helpers (Python package)
│   ├── security/            # Auth / policy helpers
│   └── storage/             # Storage connector abstractions
│
├── scripts/                 # Ops & dev automation (categorized)
│   ├── README.md            # Category index
│   ├── MIGRATION.md         # Old → new script paths
│   ├── lib/common.sh        # OMEIA_REPO_ROOT / OMEIA_SCRIPTS_ROOT
│   ├── dev/                 # start_backend, load_env, docker_bootstrap
│   ├── auth/                # Route audit, authz injection
│   ├── database/            # Migrations, seeds, catalog build
│   ├── ingest/              # Qdrant, vault, lab knowledge
│   ├── digitalization/      # Inventory, twins, enrichment pipelines
│   ├── sync/                # Supabase sync
│   ├── search/              # Portable search setup, QA eval
│   ├── document-library/    # Research KB, category trees
│   ├── llm/                 # Ollama, tunnels
│   ├── docker/              # Imaging worker, biomodels stack
│   ├── imaging/             # Remote imaging worker install/sync
│   ├── network/             # Tailscale, portable Mac↔Linux
│   ├── check/               # Environment checker scripts
│   ├── ops/                 # Autonomous processor, scheduled ingest
│   └── *.sh / *.py          # Backward-compat wrappers → subfolders
│
├── configs/                 # Environment templates, agent categories, secrets dir
├── deploy/university-desktop/  # systemd, launchd, Caddy/nginx examples
├── docker/                  # Dockerfiles (imaging-worker, biomedical-models)
├── docs/                    # Architecture, setup, runbooks
├── sql/                     # PostgreSQL migrations
├── tests/                   # pytest suite
├── tools/audit/             # Document library audit tooling
├── synthetic_data/          # Demo CSV registries
├── schemas/                 # JSON schemas
├── prompts/                 # LLM prompt templates
└── CSC/                     # University CSC / Lumi onboarding assets
```

## External data (not in repo)

| Path | Role |
|------|------|
| `../OMEIA-database/` | Canonical lab file mirror (`DATABASE_ROOT`) |
| `DATABASE_ROOT/projects/` | Per-project folders for digital twins |
| Mounted P-drive / lab SMB | `LAB_STORAGE_ROOT` when configured |

## Key entry points

| Task | Command |
|------|---------|
| Dev API | `./scripts/dev/start_backend.sh` |
| Dev UI | `./scripts/dev/start_frontend.sh` |
| Full stack | `./start.sh` |
| Autonomous pipeline | `./scripts/ops/autonomous_processor.sh start` |
| Search indexes | `./scripts/search/setup_search_portable.sh` |
| Research KB | `./scripts/document-library/setup_research_knowledge.sh` |

## Related docs

- [FRONTEND_BACKEND_TUTORIAL.md](FRONTEND_BACKEND_TUTORIAL.md) — split dev architecture
- [scripts/MIGRATION.md](../scripts/MIGRATION.md) — script path changes
- [28_AUTONOMOUS_PROCESSOR.md](28_AUTONOMOUS_PROCESSOR.md) — background processor
- [32_SEARCH_PORTABLE_SETUP.md](32_SEARCH_PORTABLE_SETUP.md) — search setup
