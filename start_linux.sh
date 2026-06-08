#!/usr/bin/env bash
# Single Linux launcher: Docker + FastAPI + Vite (one terminal).
# Same as: ./scripts/start_linux.sh
export OMEIA_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${OMEIA_REPO_ROOT}/scripts/start_linux.sh" "$@"
