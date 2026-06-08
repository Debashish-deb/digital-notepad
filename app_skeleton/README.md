# Legacy path stub (`app_skeleton/`)

Application code moved in the production layout refactor:

| Component | New location |
|-----------|--------------|
| FastAPI backend | `apps/api/src/app_skeleton/` |
| React frontend | `apps/web/` |
| Docker Compose | `infra/compose/docker-compose.yml` (root symlink) |
| Ops scripts | `infra/scripts/` (root `scripts/` symlink) |
| Environment | `config/env/` (root `configs/` symlink) |

Python imports remain `app_skeleton.*` — set `PYTHONPATH=apps/api/src` (launchers and `Makefile` do this).
