#!/bin/bash
# OMEIA / Farkki platform launcher (repo root)

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

if [ -f "$BACKEND_DIR/configs/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$BACKEND_DIR/configs/.env"
  set +a
fi

echo "Starting OMEIA Research Platform..."
echo "  REPO:     $OMEIA_REPO_ROOT"
echo "  DATABASE: $DATABASE_ROOT"

cleanup() {
  echo -e "\nStopping platform services..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}

trap cleanup SIGINT SIGTERM

echo "FastAPI backend http://localhost:8000"
cd "$BACKEND_DIR" || exit 1
"$VENV_UVICORN" app_skeleton.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "Vite frontend http://localhost:5173"
cd "$FRONTEND_DIR" || exit 1
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

wait $BACKEND_PID $FRONTEND_PID
