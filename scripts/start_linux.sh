#!/usr/bin/env bash
# OMEIA Linux — one command: Docker (Postgres, Qdrant, Ollama) + FastAPI :8000 + Vite :5173
#
# Usage:
#   ./scripts/start_linux.sh              # daily (same as ./start_linux.sh)
#   ./scripts/start_linux.sh --setup      # first boot: pull Ollama models
#   ./scripts/start_linux.sh --prod       # build UI, serve on :8000 only
#   ./scripts/start_linux.sh --api-only   # API + Docker, no frontend
exec "$(cd "$(dirname "$0")" && pwd)/dev/start_linux_desktop.sh" "$@"
