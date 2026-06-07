#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/ingest/ingest_documents_demo.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/ingest/ingest_documents_demo.py" "$@"
