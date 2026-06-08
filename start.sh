#!/bin/bash
# OMEIA / Farkki platform launcher (repo root)
#
# Starts FastAPI on :8000, waits until /ready responds, then starts Vite on :5173.
#
# Split architecture (recommended for development):
#   ./scripts/dev/start_backend.sh   # API only
#   ./scripts/dev/start_frontend.sh  # UI only (backend must be up)
# Tutorial: docs/FRONTEND_BACKEND_TUTORIAL.md

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_ROOT"
FRONTEND_DIR="$BACKEND_DIR/web"
VENV_UVICORN="$BACKEND_DIR/.venv-local/bin/uvicorn"
if [ ! -x "$VENV_UVICORN" ]; then
  VENV_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"
fi

export OMEIA_REPO_ROOT="$PROJECT_ROOT"
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:$PYTHONPATH}"
export DATABASE_ROOT="${DATABASE_ROOT:-$PROJECT_ROOT/../OMEIA-database}"
export PROJECTS_ROOT="${PROJECTS_ROOT:-$DATABASE_ROOT/projects}"

# Load .env via python-dotenv (avoids shell executing bare URL/curl lines).
if [ -f "$BACKEND_DIR/configs/.env" ]; then
  # shellcheck disable=SC1091
  eval "$("$BACKEND_DIR/scripts/dev/load_env.sh" "$BACKEND_DIR/configs/.env")"
fi

# Portable remote LLM (Tailscale Linux workstation) — overrides .env localhost URLs.
if [ -n "${TAILSCALE_LINUX_IP:-}" ]; then
  export OLLAMA_BASE_URL="http://${TAILSCALE_LINUX_IP}:11434/v1"
  export QDRANT_URL="http://${TAILSCALE_LINUX_IP}:6333"
  # Mac thin client: Docker stack runs on Linux, not on this machine.
  export DOCKER_LOCAL=false
  export DOCKER_AUTO_START=false
fi
export OMEIA_REPO_ROOT="${OMEIA_REPO_ROOT:-$PROJECT_ROOT}"
export DATABASE_ROOT="${DATABASE_ROOT:-$PROJECT_ROOT/../OMEIA-database}"
export PROJECTS_ROOT="${PROJECTS_ROOT:-$DATABASE_ROOT/projects}"
export OMEIA_FRONTEND_MODE="${OMEIA_FRONTEND_MODE:-dev}"
if [ -z "${FIREBASE_SERVICE_ACCOUNT_PATH:-}" ] && [ -f "$PROJECT_ROOT/configs/secrets/firebase-adminsdk.json" ]; then
  export FIREBASE_SERVICE_ACCOUNT_PATH="$PROJECT_ROOT/configs/secrets/firebase-adminsdk.json"
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo -e "\nStopping platform services..."
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null
  fi
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null
  fi
  wait 2>/dev/null
  exit 0
}

trap cleanup SIGINT SIGTERM

free_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "Stopping existing process(es) on port $port..."
    kill $pids 2>/dev/null || true
    sleep 1
  fi
}

wait_for_backend() {
  local live_url="http://127.0.0.1:8000/live"
  local ready_url="http://127.0.0.1:8000/ready"
  local timeout=60
  local elapsed=0

  echo "Waiting for API readiness at $ready_url (up to ${timeout}s)..."
  while [ "$elapsed" -lt "$timeout" ]; do
    if curl -sf "$ready_url" >/dev/null 2>&1; then
      echo "API is ready."
      return 0
    fi
    if curl -sf "$live_url" >/dev/null 2>&1; then
      :
    fi
    sleep 1
    elapsed=$((elapsed + 1))
    if [ $((elapsed % 5)) -eq 0 ]; then
      echo "  still waiting... (${elapsed}s)"
    fi
  done

  echo "ERROR: API did not become ready within ${timeout}s."
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null
  fi
  exit 1
}

echo "Starting OMEIA Research Platform..."
echo "  REPO:          $OMEIA_REPO_ROOT"
echo "  DATABASE:      $DATABASE_ROOT"
echo "  FRONTEND_MODE: $OMEIA_FRONTEND_MODE (dev=Vite :5173 | prod=dist on :8000)"

# Auto-verify / start Docker stack when Docker runs locally (skip when DOCKER_LOCAL=false).
if [ "${DOCKER_LOCAL:-true}" = "false" ] || [ "${DOCKER_LOCAL:-true}" = "0" ]; then
  echo "DOCKER_LOCAL=false — API only on this machine (LLM/DB on remote host)."
else
  if [ -x "$PROJECT_ROOT/scripts/dev/docker_bootstrap.sh" ]; then
    "$PROJECT_ROOT/scripts/dev/docker_bootstrap.sh" || echo "WARN: Docker bootstrap incomplete — API will use fallbacks."
    export DOCKER_COMPOSE_STARTED=true
  fi
fi

free_port 8000

if [ "$OMEIA_FRONTEND_MODE" = "prod" ]; then
  echo "Building production frontend..."
  bash "$PROJECT_ROOT/scripts/dev/build_frontend_prod.sh"
  export OMEIA_SERVE_FRONTEND_STATIC=true
else
  free_port 5173
fi

echo "FastAPI backend http://localhost:8000"
cd "$BACKEND_DIR" || exit 1
if [ "$OMEIA_FRONTEND_MODE" = "prod" ]; then
  "$VENV_UVICORN" omeia.api.main:app --host 0.0.0.0 --port 8000 &
else
  "$VENV_UVICORN" omeia.api.main:app --host 0.0.0.0 --port 8000 --reload &
fi
BACKEND_PID=$!

wait_for_backend || exit 1

if [ "$OMEIA_FRONTEND_MODE" = "prod" ]; then
  echo "Production UI served from API http://localhost:8000"
  wait $BACKEND_PID
else
  if [ -z "${VITE_HMR_HOST:-}" ] && [ -n "${TAILSCALE_LINUX_IP:-}" ]; then
    export VITE_HMR_HOST="${TAILSCALE_LINUX_IP}"
  fi
  if [ -z "${VITE_HMR_HOST:-}" ] && command -v tailscale >/dev/null 2>&1; then
    _ts_ip="$(tailscale ip -4 2>/dev/null | head -1 | tr -d '[:space:]')"
    if [ -n "$_ts_ip" ]; then
      export VITE_HMR_HOST="$_ts_ip"
    fi
  fi
  echo "Vite frontend http://localhost:5173"
  if [ -n "${VITE_HMR_HOST:-}" ]; then
    echo "  Remote UI (Mac/Tailscale): http://${VITE_HMR_HOST}:5173 — live reload enabled"
  fi
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/scripts/dev/ensure_node_for_vite.sh"
  cd "$FRONTEND_DIR" || exit 1
  echo "Starting Vite (Node $(node -v), npm $(npm -v))..."
  npm run dev -- --host 0.0.0.0 --port 5173 --strictPort &
  FRONTEND_PID=$!
  wait $BACKEND_PID $FRONTEND_PID
fi
