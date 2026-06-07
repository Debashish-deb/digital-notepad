# OMEIA Scripts

Operational scripts for development, ingestion, digitalization, search, deployment, and platform checks. Scripts live in **category folders** under `scripts/`; thin **backward-compat wrappers** remain at `scripts/<name>.sh` (and some `.py`) for older docs and bookmarks.

## Shared paths

Source `scripts/lib/common.sh` from any shell script:

```bash
# From scripts/<category>/foo.sh (one level below scripts/)
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"
# Then use: $OMEIA_REPO_ROOT, $OMEIA_SCRIPTS_ROOT, omeia_load_env
```

Python scripts should resolve the repo root as:

```python
REPO_ROOT = Path(__file__).resolve().parents[2]
```

Or honor `OMEIA_REPO_ROOT` when set.

## Categories

| Folder | Purpose |
|--------|---------|
| `dev/` | Local development: backend/frontend startup, env loading, Docker bootstrap, portable Mac launcher |
| `auth/` | Authorization utilities (route audit, authz injection) |
| `database/` | SQL migrations, seed data, synthetic registries, projects catalog |
| `ingest/` | Qdrant collections, vault ingest, lab knowledge, document demos |
| `digitalization/` | Raw asset inventory, metadata enrichment, project digital twins, pipeline runners |
| `sync/` | Supabase document sync, allowlist sync |
| `search/` | Portable search setup, QA harnesses, AI lab assistant eval |
| `document-library/` | Research knowledge base setup, category trees, duplicate cleanup |
| `llm/` | Ollama setup, model pulls, SSH tunnel, Gemini smoke tests |
| `docker/` | Imaging worker build, biomedical models stack, Linux Docker stack |
| `imaging/` | Imaging worker bundles, Linux paste-install, sync to remote hosts |
| `network/` | Tailscale/portable Mac↔Linux networking, env apply, connectivity tests |
| `check/` | Environment checkers (Python, GPU, Docker, napari, lumi, cylinter, project structure) |
| `ops/` | Autonomous processor, scheduled ingest, platform validation, vectorization queue |
| `lib/` | Shared shell helpers (`common.sh`) |
| `profile/` | *(placeholder)* profiling utilities |
| `firewall/` | *(placeholder)* firewall helpers |
| `detection/` | *(placeholder)* detection pipelines |

## Quick start

```bash
./scripts/dev/start_backend.sh    # API :8000
./scripts/dev/start_frontend.sh   # UI :5173
./start.sh                        # both

./scripts/ops/autonomous_processor.sh start
./scripts/search/setup_search_portable.sh
```

See [MIGRATION.md](MIGRATION.md) for old flat-path → new path mapping.
