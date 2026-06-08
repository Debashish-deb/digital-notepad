#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

rm -rf apps infra config 2>/dev/null || true

mkdir -p apps/api/src apps/web infra/compose infra/docker infra/scripts config/env docs/architecture

# API + supporting packages (preserve omeia.* imports)
mkdir -p apps/api/src/omeia
git mv omeia/api omeia/security omeia/data omeia/storage omeia/digitalization omeia/pipelines apps/api/src/omeia/
touch apps/api/src/omeia/__init__.py

# Frontend
if [[ ! -f apps/web/package.json ]]; then
  git mv omeia/ui/react_frontend apps/web-tmp
  mkdir -p apps/web
  git mv apps/web-tmp/* apps/web/ 2>/dev/null || mv apps/web-tmp/* apps/web/
  rmdir apps/web-tmp 2>/dev/null || rm -rf apps/web-tmp
fi

# Infra
git mv docker-compose.yml docker-compose.biomodels.yml docker-compose.imaging.yml infra/compose/
git mv docker infra/docker
git mv scripts infra/scripts
git mv configs config/env

# Symlinks (backward compat)
ln -sfn config/env configs
ln -sfn infra/scripts scripts
ln -sfn infra/compose/docker-compose.yml docker-compose.yml
ln -sfn infra/compose/docker-compose.biomodels.yml docker-compose.biomodels.yml
ln -sfn infra/compose/docker-compose.imaging.yml docker-compose.imaging.yml

cp apps/api/src/omeia/api/requirements.txt apps/api/requirements.txt

# Legacy stub
mkdir -p omeia
cat > omeia/README.md <<'STUB'
# Legacy path stub

Code moved to `apps/api/src/omeia/` — imports remain `omeia.*`.

Use `make install && make start` from the repository root.
STUB

echo "Physical moves done."
