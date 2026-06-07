#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/dev/start_frontend.sh
exec "$(dirname "$0")/dev/start_frontend.sh" "$@"
