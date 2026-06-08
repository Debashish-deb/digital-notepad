#!/usr/bin/env bash
# Single Linux launcher: Docker + FastAPI + Vite (one terminal).
# Same as: ./scripts/start_linux.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/start_linux.sh" "$@"
