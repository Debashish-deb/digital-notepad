# Safe Hardening Pass — 2026-06-07

Follow-up to [global_app_audit_fix_report.md](./global_app_audit_fix_report.md).  
No product behavior changes, no data deletion, production error visibility preserved.

---

## Executive summary

| Area | Outcome |
|------|---------|
| Test environment safety | Production Supabase blocked during pytest; runtime DB skips |
| Data reorganization | Dry-run quarantine script + manifest outputs (no moves without `--confirm`) |
| ESLint phase 1 | 281 → **235** problems (−46); 39 unused React imports removed |
| Image viewer | Implementation plan written (no full viewer built) |
| Bundle | Build passes; Three.js remains lazy-loaded on 3 routes only |

---

## 1. Test environment safety

### Changes

| File | Why safe |
|------|----------|
| `tests/conftest.py` | Sets `OMEIA_PYTEST=1`, strips hosted Supabase secrets unless `OMEIA_ALLOW_PRODUCTION_DB_TESTS=1`; runtime skip hook for `requires_database` |
| `tests/db_safety.py` | DSN resolution, `postgres_reachable()`, markers, skip reasons |
| `tests/test_db_safety_unit.py` | Guards unit tests (no live DB) |
| `app_skeleton/api/supabase_config.py` | `postgres_conn()` uses test resolver only when `OMEIA_PYTEST=1` — production path unchanged |
| `tests/test_project_digitalization.py` | `@pytest.mark.requires_database` + class `SkipTest` when DB down |
| `tests/test_lab_storage_api.py` | Runtime `skipTest` for registry/ingestion endpoints |
| `tests/test_supabase_sync.py` | Live integration requires `OMEIA_ALLOW_PRODUCTION_DB_TESTS=1` |
| `pytest.ini` | Documented markers |
| `docs/TESTING.md` | Local / CI / network / opt-in production instructions |

### Behavior

- **Never** silently uses production `SUPABASE_DB_PASSWORD` during pytest.
- Order: `TEST_DATABASE_URL` → `TEST_SUPABASE_URL` → `POSTGRES_CONN` → local default DSN.
- DB-backed tests **skip** with `SKIP_REASON_NO_DB` when Postgres is unreachable (runtime check, not import-time).

---

## 2. Data reorganization safety

### Script: `scripts/data_reorg_quarantine.py`

**Default: dry-run only.** No files moved or deleted.

Outputs per run under `reports/smart_reorganization/quarantine_runs/{timestamp}/`:

- `files_to_move.csv` (225 rows in latest dry-run)
- `duplicates_to_review.csv` (15 rows)
- `quarantine_manifest.json`
- `restore_plan.json`

Apply quarantine duplicates/placeholders only with:

```bash
python3 scripts/data_reorg_quarantine.py --apply --confirm
```

Moves go to `reports/99_quarantine_review/{timestamp}/` with checksum verification. **No deletes.**

---

## 3. ESLint phase 1

| Action | Count |
|--------|-------|
| Removed unused `import React` from 39 JSX files | −39 errors |
| Dead code: `MetaRow`, `FILE_TYPE_LABELS` in `ScientificFileExplorer.jsx` | −2 |
| Unused imports in `TaskpadSheet.jsx` | −2 |
| `App.jsx` static stats/team/auditLogs (removed unused setters) | −3 |
| **Remaining** | **235** (208 errors, 27 warnings) |

**Not changed:** React hook dependency arrays, `react-refresh/only-export-components`, global rule disables.

---

## 4. Image viewer gap analysis

Plan: [`reports/image_viewer_implementation_plan.md`](./image_viewer_implementation_plan.md)

Backend tile/manifest/thumbnail routes exist. Frontend placeholder loads manifest + thumbnail only. Full OME-TIFF canvas deferred to phased plan (no Three.js required).

---

## 5. Bundle check

`npm run build` — **PASS**

Three.js / `@react-three/*` imports (all lazy):

| Consumer | Route / context |
|----------|-----------------|
| `Pipeline3DScene.jsx` | CyCIF imaging pipeline tab |
| `LoginOvarianScene.jsx` | Login screen |
| `ModelViewer3D.jsx` | Project folder / document 3D previews |

`three-vendor` chunk (~997 KB) not in initial bundle; loaded on demand. **No dependency removed** (still required by above routes).

---

## Validation results

| Command | Result |
|---------|--------|
| `npm run build` | **PASS** |
| `npm run lint` | **235 problems** (was 281) |
| `pytest tests/ -q` (offline / no local Postgres) | **150 passed, 10 skipped** |
| `pytest tests/ -q` (network, Supabase creds stripped) | **150 passed, 10 skipped** |
| `python3 scripts/data_reorg_quarantine.py` | **PASS** (dry-run artifacts emitted) |

---

## Files changed (summary)

**Tests / backend:** `tests/conftest.py`, `tests/db_safety.py`, `tests/test_db_safety_unit.py`, `tests/test_lab_storage_api.py`, `tests/test_project_digitalization.py`, `tests/test_supabase_sync.py`, `pytest.ini`, `app_skeleton/api/supabase_config.py`

**Scripts / docs:** `scripts/data_reorg_quarantine.py`, `docs/TESTING.md`, `reports/image_viewer_implementation_plan.md`, `reports/hardening_pass_2026-06-07.md`

**Frontend (ESLint phase 1):** 39 JSX files (React import cleanup), `App.jsx`, `ScientificFileExplorer.jsx`, `TaskpadSheet.jsx`

---

## Remaining risks

1. **208 ESLint errors** — mostly hooks deps and react-refresh exports; needs phased PRs.
2. **Roihu tab** — still “Coming soon” (content, not wiring).
3. **Full tile viewer** — not implemented; large feature.
4. **Qdrant offline** — vector ingest stub when Qdrant down (unchanged).
5. **Data layout migration** — 225 proposed moves still need human review + API path updates before any apply.

---

## Items needing user approval

1. **Run quarantine apply** — `scripts/data_reorg_quarantine.py --apply --confirm` (moves 15 duplicate/placeholder files into quarantine).
2. **Full smart reorganization** — 225 `files_to_move.csv` entries (high-risk API path changes).
3. **Duplicate review queue** — 61 rows in `duplicate_review_queue.csv`.
4. **Mass ESLint phase 2** — hook dependency and export-split churn.
5. **Production DB integration tests** — set `OMEIA_ALLOW_PRODUCTION_DB_TESTS=1` only in controlled CI job.
6. **OME-TIFF viewer implementation** — follow plan in `image_viewer_implementation_plan.md`.
