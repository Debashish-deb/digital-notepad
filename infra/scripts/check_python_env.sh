#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/check/check_python_env.sh
exec "$(dirname "$0")/check/check_python_env.sh" "$@"
