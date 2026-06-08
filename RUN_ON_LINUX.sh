#!/usr/bin/env bash
# RUN_ON_LINUX.sh — one-shot Linux workstation deploy after `git pull` (no Mac SSH/SCP).
#
# Usage (Linux only):
#   cd ~/data4TB/digital-notepad   # or your clone root
#   chmod +x RUN_ON_LINUX.sh
#   ./RUN_ON_LINUX.sh
#
# Mac pushes code via GitHub; run this script on the Linux host to sync branch, env, deps,
# Qdrant collections, SQL migration, bootstrap, and health checks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export OMEIA_REPO_ROOT="$ROOT"

BRANCH="${OMEIA_LINUX_BRANCH:-cursor/unified-search-ai-lab-assistant}"
API_BASE="${OMEIA_API_BASE:-http://127.0.0.1:8000}"

echo "=== OMEIA RUN_ON_LINUX ==="
echo "  Host: $(hostname)"
echo "  Repo: $ROOT"
echo "  Branch: $BRANCH"

echo "--- Git sync ---"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH" || git pull origin "$BRANCH"

ENV_FILE="$ROOT/configs/.env"
TEMPLATE="$ROOT/configs/linux-workstation.env.template"
if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$TEMPLATE" ]]; then
    cp "$TEMPLATE" "$ENV_FILE"
    echo "  Created configs/.env from linux-workstation.env.template"
  else
    echo "WARN: configs/.env missing and no template at $TEMPLATE"
  fi
else
  echo "  configs/.env present (unchanged)"
fi

if [[ -f "$ROOT/scripts/dev/load_env.sh" && -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ENV_FILE")" 2>/dev/null || true
fi

PY=""
for candidate in \
  "$ROOT/.venv-local/bin/python3" \
  "$ROOT/.venv/bin/python3" \
  "$(command -v python3 2>/dev/null || true)"; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    PY="$candidate"
    break
  fi
done

REQ="$ROOT/requirements.txt"
if [[ ! -d "$ROOT/.venv" && ! -d "$ROOT/.venv-local" ]]; then
  echo "--- Python venv + requirements ---"
  if [[ -z "$PY" ]]; then
    echo "ERROR: python3 not found"
    exit 1
  fi
  "$PY" -m venv "$ROOT/.venv"
  PY="$ROOT/.venv/bin/python3"
  "$PY" -m pip install -U pip wheel
  if [[ -f "$REQ" ]]; then
    "$PY" -m pip install -r "$REQ"
  else
    echo "WARN: $REQ not found; skipping pip install"
  fi
elif [[ -f "$REQ" && -n "$PY" ]]; then
  echo "--- Quick pip check (requirements.txt) ---"
  "$PY" -m pip install -q -r "$REQ" || echo "WARN: pip install -r requirements.txt had issues (continuing)"
else
  echo "--- Python env OK (venv present) ---"
fi

QDRANT_SCRIPT="$ROOT/infra/scripts/ingest/ensure_runtime_qdrant_collections.py"
if [[ ! -f "$QDRANT_SCRIPT" ]]; then
  echo "WARN: missing $QDRANT_SCRIPT — skip Qdrant ensure"
else
  echo "--- Ensure runtime Qdrant collections ---"
  PYTHONPATH="$ROOT" "$PY" "$QDRANT_SCRIPT"
fi

echo "--- SQL migration (continuous learning) ---"
if ! command -v psql >/dev/null 2>&1; then
  echo "WARN: psql not in PATH — skip sql/150_continuous_learning.sql"
elif [[ -z "${POSTGRES_CONN:-}" ]]; then
  echo "WARN: POSTGRES_CONN unset — skip sql/150_continuous_learning.sql"
elif [[ ! -f "$ROOT/sql/150_continuous_learning.sql" ]]; then
  echo "WARN: sql/150_continuous_learning.sql not found — skip"
else
  if psql "$POSTGRES_CONN" -v ON_ERROR_STOP=0 -f "$ROOT/sql/150_continuous_learning.sql"; then
    echo "  Applied (or already present) sql/150_continuous_learning.sql"
  else
    echo "WARN: psql apply returned non-zero (migration may already be applied)"
  fi
fi

echo "--- Linux bootstrap (skip-docker) ---"
if [[ -x "$ROOT/scripts/deploy/linux_bootstrap_all.sh" ]]; then
  ./scripts/deploy/linux_bootstrap_all.sh --skip-docker
elif [[ -x "$ROOT/infra/scripts/deploy/linux_bootstrap_all.sh" ]]; then
  ./infra/scripts/deploy/linux_bootstrap_all.sh --skip-docker
else
  echo "ERROR: linux_bootstrap_all.sh not found"
  exit 1
fi

START_SCRIPT="$ROOT/scripts/start_linux.sh"
if [[ ! -x "$START_SCRIPT" ]]; then
  echo "WARN: $START_SCRIPT missing — start stack manually"
else
  if curl -sf "${API_BASE}/live" >/dev/null 2>&1; then
    echo "--- API already reachable at ${API_BASE} — not starting duplicate stack ---"
  else
    echo "--- Starting stack in background (./scripts/start_linux.sh) ---"
    LOG_DIR="$ROOT/logs"
    mkdir -p "$LOG_DIR"
    nohup "$START_SCRIPT" >>"$LOG_DIR/run_on_linux_start.log" 2>&1 &
    echo "  PID $! — log: $LOG_DIR/run_on_linux_start.log"
    echo "  Waiting for /live (up to 120s)..."
    for _ in $(seq 1 24); do
      if curl -sf "${API_BASE}/live" >/dev/null 2>&1; then
        break
      fi
      sleep 5
    done
  fi
fi

echo "--- Health checks ---"
for path in /live /ready; do
  url="${API_BASE}${path}"
  if curl -sf "$url" | head -c 2000; then
    echo ""
    echo "  OK $url"
  else
    echo "  FAIL $url (is ./scripts/start_linux.sh running?)"
  fi
  echo ""
done

TS_IP=""
if command -v tailscale >/dev/null 2>&1; then
  TS_IP="$(tailscale ip -4 2>/dev/null | head -1 || true)"
fi
if [[ -n "$TS_IP" ]]; then
  echo "Browser (Tailscale): http://${TS_IP}:5173"
  echo "API (Tailscale):     http://${TS_IP}:8000"
else
  echo "Tailscale IP not available — on Linux run: tailscale ip -4"
  echo "Then open: http://<tailscale-ip>:5173"
fi

echo "=== RUN_ON_LINUX complete ==="
