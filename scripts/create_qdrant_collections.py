#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/ingest/create_qdrant_collections.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/ingest/create_qdrant_collections.py" "$@"
