#!/bin/bash
# OMEIA / Farkki platform launcher (repo root)
#
# Starts FastAPI on :8000, waits until /health responds, then starts Vite on :5173.
#
# Split architecture (recommended for development):
#   ./scripts/dev/start_backend.sh   # API only
#   ./scripts/dev/start_frontend.sh  # UI only (backend must be up)
# Tutorial: docs/FRONTEND_BACKEND_TUTORIAL.md

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_ROOT"
FRONTEND_DIR="$BACKEND_DIR/app_skeleton/ui/react_frontend"
VENV_UVICORN="$BACKEND_DIR/.venv-local/bin/uvicorn"
if [ ! -x "$VENV_UVICORN" ]; then
  VENV_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"
fi

export OMEIA_REPO_ROOT="$PROJECT_ROOT"
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
  local url="http://127.0.0.1:8000/health"
  local timeout=60
  local elapsed=0

  echo "Waiting for API at $url (up to ${timeout}s)..."
  while [ "$elapsed" -lt "$timeout" ]; do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "API is ready."
      return 0
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
echo "  REPO:     $OMEIA_REPO_ROOT"
echo "  DATABASE: $DATABASE_ROOT"

# Auto-verify / start Docker stack when Docker runs locally (skip when DOCKER_LOCAL=false).
if [ "${DOCKER_LOCAL:-true}" = "false" ] || [ "${DOCKER_LOCAL:-true}" = "0" ]; then
  echo "DOCKER_LOCAL=false — API only on this machine (LLM/DB on remote host)."
else
  if [ -x "$PROJECT_ROOT/scripts/dev/docker_bootstrap.sh" ]; then
    "$PROJECT_ROOT/scripts/dev/docker_bootstrap.sh" || echo "WARN: Docker bootstrap incomplete — API will use fallbacks."
  fi
fi

free_port 8000
free_port 5173

echo "FastAPI backend http://localhost:8000"
cd "$BACKEND_DIR" || exit 1
"$VENV_UVICORN" app_skeleton.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

wait_for_backend || exit 1

echo "Vite frontend http://localhost:5173"
cd "$FRONTEND_DIR" || exit 1
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort &
FRONTEND_PID=$!

wait $BACKEND_PID $FRONTEND_PID
