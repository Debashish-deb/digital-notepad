# Testing guide (OMEIA-AI)

## Quick commands

```bash
# From repo root — unit tests (no production Supabase)
pytest tests/ -q

# Frontend
cd app_skeleton/ui/react_frontend && npm run build && npm run lint
```

## Test database safety

Pytest sets `OMEIA_PYTEST=1` automatically via `tests/conftest.py`.

**Production Supabase credentials are stripped** from the environment at pytest startup unless you explicitly opt in with:

```bash
export OMEIA_ALLOW_PRODUCTION_DB_TESTS=1
```

Never rely on `configs/.env` hosted passwords during normal unit tests.

### Connection resolution order (pytest only)

1. `TEST_DATABASE_URL` or `TEST_SUPABASE_URL`
2. `POSTGRES_CONN` (local Docker / dev Postgres)
3. Default local DSN: `postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai`
4. Hosted Supabase **only** if `OMEIA_ALLOW_PRODUCTION_DB_TESTS=1`

### Skipping DB-backed tests

Tests that need a live Postgres connection are skipped with a clear reason when the database is unreachable. Helpers live in `tests/db_safety.py`:

- `requires_database` — pytest marker
- `postgres_reachable()` — runtime check
- `resolve_test_postgres_conn()` — safe DSN for assertions

## Running locally

### Without network (CI-style)

```bash
pytest tests/ -q
```

DB-backed tests skip or fail fast if local Postgres is not running. No production Supabase is contacted when credentials are only in `configs/.env`.

### With local Postgres

```bash
export POSTGRES_CONN=postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai
pytest tests/ -q
```

### With explicit test database

```bash
export TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/farkki_ai_test
pytest tests/ -q
```

### With production Supabase integration (opt-in only)

```bash
export OMEIA_ALLOW_PRODUCTION_DB_TESTS=1
export SUPABASE_DB_PASSWORD=...
export SUPABASE_SYNC_INTEGRATION=1   # only for test_supabase_sync live test
pytest tests/test_supabase_sync.py -q
```

## Markers

| Marker | Meaning |
|--------|---------|
| `requires_database` | Needs reachable test Postgres |
| `requires_production_db` | Needs `OMEIA_ALLOW_PRODUCTION_DB_TESTS=1` |

Register in `pytest.ini` if adding new markers.

## Frontend validation

```bash
cd app_skeleton/ui/react_frontend
npm run build    # must pass before merge
npm run lint     # incremental cleanup; hook deps not mass-changed in phase 1
```
