# Application code (`app_skeleton`)

**Name:** `app_skeleton` is legacy from the original “blueprint scaffold” phase. The code here is the live platform (API, React UI, data, pipelines)—not a throwaway skeleton. A rename to something like `app/` or `platform/` is planned but touches the Python package name (`app_skeleton.api`), Docker, tests, and hundreds of import paths.

## Run from inside the app (no need to memorize `scripts/`)

| What | From this folder | Command |
|------|------------------|---------|
| **API** | `app_skeleton/api/` | `./dev.sh` |
| **React UI** | `app_skeleton/ui/react_frontend/` | `./dev.sh` or `npm run dev` |
| **Both** | repo root | `./start.sh` |

The API must still use the **repository root** as its working directory internally (for `configs/.env`, `app_skeleton/data/`, and `OMEIA_REPO_ROOT`). The `dev.sh` wrappers handle that for you.

## Layout

```
app_skeleton/
  api/                 FastAPI backend (port 8000)
  ui/react_frontend/   React SPA (port 5173)
  ui/streamlit_app.py  Legacy Streamlit (optional)
  data/                Runtime JSON, processor state
  pipelines/           LUMI image-processing pipeline
  digitalization/      Digital twin helpers
```

Repo-wide ops (ingest, migrations, search QA) stay under top-level `scripts/` because they touch `configs/`, `sql/`, `tests/`, and external `DATABASE_ROOT`—not just the web app.
