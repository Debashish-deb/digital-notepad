#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/database/apply_sql_migrations.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/database/apply_sql_migrations.py" "$@"
