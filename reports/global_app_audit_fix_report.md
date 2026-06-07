# Global App Audit & Fix Report
Date: 2026-06-07

## Executive Summary

A full-repo audit covered frontend (`app_skeleton/ui/react_frontend`), backend (`app_skeleton/api`), tests, scripts, and navigation wiring. The production frontend **build passes**, and after fixes **154 Python tests pass** (3 skipped) when run with network access to Supabase.

**Safe fixes applied (11 items):** pytest import path configuration, ProjectsScreen API URL wiring, digitalization chunker ID bug, several dead-code/lint cleanups in frontend utils, ESLint node globals for `vite.config.js`, and `pageMeta.js` refactor to use its existing selector map.

**Not fixed without approval:** database migrations, data deletion/reorganization, auth/credential changes, mass ESLint rule relaxation, and API contract changes for offline DB graceful degradation.

## Methodology

1. **Grep sweep** across `app_skeleton/` for `TODO`, `FIXME`, `HACK`, `stub`, `placeholder`, `WIP`, `coming soon`, `not implemented`.
2. **Navigation audit** — cross-checked `navigation.js` screen IDs against `App.jsx` `switch` cases; all mapped screens resolve to implemented components.
3. **Build & lint** — `npm run build` and `npm run lint` in `app_skeleton/ui/react_frontend`.
4. **Tests** — `pytest tests/ -q` from repo root (with `pytest.ini` `pythonpath = .`).
5. **Targeted code review** — agent orchestrator wiring, data layout paths, chunker/registry, API router registration in `main.py`.
6. **Prior audit docs** — skimmed `docs/33_AI_LAB_ASSISTANT_PRODUCTION_PLAN.md`, `docs/34_AI_LAB_ASSISTANT_AND_SEARCH_DEEP_AUDIT.md` for known gap classes.

## Issues Found

| ID | Severity | Area | Description | Status |
|----|----------|------|-------------|--------|
| AUD-001 | High | Tests | `pytest` failed to collect 17 modules — `app_skeleton` and `tests.auth_fixtures` not on `PYTHONPATH`; `tests/` not a package | **Fixed** (`pytest.ini`, `tests/__init__.py`) |
| AUD-002 | Medium | Frontend | `ProjectsScreen` received `API_URL` (module default) instead of `resolvedApiUrl` from `ApiContext` — wrong backend when context overrides URL | **Fixed** (`App.jsx`) |
| AUD-003 | High | Digitalization | `chunker.chunk_document()` set `canonical_document_id` from `canonical.id` only; in-memory/test docs use `document_id`, yielding empty string | **Fixed** (`chunker.py` fallback) |
| AUD-004 | Low | Frontend lint | `vite.config.js` used `process` without Node ESLint globals | **Fixed** (`eslint.config.js`) |
| AUD-005 | Low | Frontend utils | Dead/unused symbols: `META_SELECTORS`, `MIN_FILES_FOR_SUBFOLDER_TABS`, `normalizeRelPath` import, `_contentRoot` param, `SPREADSHEET_XML_DUMP` duplicate | **Fixed** |
| AUD-006 | Low | Frontend utils | `spreadsheetPreview.js` useless `end` assignment flagged by ESLint | **Fixed** |
| AUD-007 | Info | ESLint | 281 lint problems remain (254 errors, 27 warnings) — mostly `no-unused-vars`, `react-hooks/exhaustive-deps`, `react-refresh/only-export-components` | Open |
| AUD-008 | Info | Computational Hub | Roihu tab shows "Coming soon" placeholder (`BioinformaticsHubScreen`, `navigation.js`) | Open (content gap) |
| AUD-009 | Info | Image viewer | `ImageViewerPlaceholderScreen` is functional but not full tile/stream viewer | Open (feature gap) |
| AUD-010 | Info | Vector search | Qdrant ingest logs "offline stub" when Qdrant unavailable (`vault.py`) | Open (infra dependency) |
| AUD-011 | Info | Data layout | Smart reorganization plan flags empty/tiny placeholder `.chunks.jsonl` files in legacy `processed_projects/` | Open (needs data migration approval) |
| AUD-012 | Info | AI assistant | Prior audits note retrieval quality (ranking, thresholding) as main quality gap — not a wiring bug | Open |
| AUD-013 | Info | Vendor code | DeepCell container `build/lib/` contains upstream TODOs | Ignored (third-party) |
| AUD-014 | Medium | Tests | DB-backed tests (`test_project_digitalization`, registry endpoints) fail without network/DNS to Supabase | Open (env dependency) |
| AUD-015 | Info | Navigation | All `navigation.js` `screen` values have matching `App.jsx` cases; legacy redirects (`CYCIF_LEGACY_NESTED`, `DATA_STORAGE_LEGACY_SUBS`) wired | Verified OK |
| AUD-016 | Info | Backend | `agent_categories` router registered in `main.py`; configs `configs/agent_categories.json` and `configs/internal_agents.json` present | Verified OK |
| AUD-017 | Info | Build | Vite chunk size warnings (>700 kB for `three-vendor`, `index`) | Open (performance) |

## Fixes Applied

| Change | Files touched |
|--------|---------------|
| Added `pytest.ini` with `pythonpath = .` and `testpaths = tests` | `pytest.ini` |
| Made `tests` importable as a package | `tests/__init__.py` |
| Pass `resolvedApiUrl` to `ProjectsScreen` | `app_skeleton/ui/react_frontend/src/App.jsx` |
| Fallback `canonical_document_id` to `document_id` when DB `id` unset | `app_skeleton/digitalization/chunker.py` |
| Node globals for Vite config linting | `app_skeleton/ui/react_frontend/eslint.config.js` |
| Use `META_SELECTORS` in `applyPageMeta()` | `app_skeleton/ui/react_frontend/src/utils/pageMeta.js` |
| Remove unused import | `app_skeleton/ui/react_frontend/src/utils/workspaceDatapadUtils.js` |
| Remove unused constant | `app_skeleton/ui/react_frontend/src/utils/documentBrowserUtils.js` |
| Remove unused `_contentRoot` parameter (API resolves root server-side) | `app_skeleton/ui/react_frontend/src/utils/digitalTwinUtils.js` |
| Consolidate office XML dump detection | `app_skeleton/ui/react_frontend/src/utils/textCleanup.js` |
| Fix useless assignment in ZIP trim loop | `app_skeleton/ui/react_frontend/src/utils/spreadsheetPreview.js` |
| Preserve valid regex; suppress false-positive `no-useless-escape` | `app_skeleton/ui/react_frontend/src/utils/kindleLayout.js` |

## Items Requiring User Approval

1. **Smart library data reorganization** — `reports/smart_reorganization/reorganization_plan.md` proposes moving/quarantining empty placeholder chunk files and restructuring `app_skeleton/data/`. Requires data migration and possible deletion.
2. **Duplicate review queue actions** — `reports/document_library_audit/metadata_v2/duplicate_review_queue.csv` (61 rows) needs human decisions before automated dedup/delete.
3. **Database schema migrations** — `sql_migrations.py` applies pending migrations against live Supabase on `ensure_vault_schema()`; running in CI/offline needs a local Postgres fixture or mock strategy.
4. **Auth / credential hardening** — Tests currently reach production Supabase when `configs/.env` credentials are present; consider dedicated test DB or `PLATFORM_AUTH_DISABLED` + SQLite stub for CI.
5. **Mass ESLint remediation** — 254 remaining errors; fixing all would touch many components (React import cleanup, hooks deps, `react-refresh` export splits). Recommend scoped ESLint config or incremental PRs.
6. **API graceful degradation** — Adding empty-list fallbacks when Postgres is unreachable would change error semantics for production monitoring.
7. **Roihu / full image streaming UI** — Content and feature completion, not bug fixes.

## Validation Results

| Command | Location | Outcome |
|---------|----------|---------|
| `npm run build` | `app_skeleton/ui/react_frontend` | **PASS** (built in ~2s; chunk size warnings only) |
| `npm run lint` | `app_skeleton/ui/react_frontend` | **FAIL** — 281 problems (254 errors, 27 warnings); down from 291 before fixes |
| `pytest tests/ -q` | repo root (no network) | **PARTIAL** — 146 passed, 3 failed, 5 errors (Supabase DNS unreachable in sandbox) |
| `pytest tests/ -q` | repo root (with network) | **PASS** — 154 passed, 3 skipped, 6 warnings in ~81s |

Skipped tests (3): environment-dependent lab section fixtures (`test_lab_section_wet_lab_extracted_count`, pagination) when twins absent on disk.

## Remaining Known Gaps

| Gap | Why not fixed |
|-----|----------------|
| Roihu supercomputer tab content | Placeholder by design; needs technical writing |
| Full OME-TIFF tile viewer (vs placeholder screen) | Large feature; streaming API exists backend-side |
| Qdrant vector indexing when offline | Requires Qdrant service or embedding policy decision |
| 254 ESLint errors | Broad stylistic/hooks churn; risk of behavior regressions |
| Empty legacy `processed_projects/*.chunks.jsonl` | Data migration — flagged for approval |
| AI Lab Assistant retrieval quality | Documented in `docs/33`/`docs/34`; needs RAG tuning not wiring |
| Chunk bundle size (three.js ~997 kB) | Performance optimization; optional code-splitting pass |
| `document_registry.list_documents()` hard-requires Postgres | No offline stub; tests need network or mock layer |

---

*Report generated by global audit pass. All listed fixes were applied and validated locally.*
