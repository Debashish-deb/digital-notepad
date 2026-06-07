#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/search/setup_search_portable.sh
exec "$(dirname "$0")/search/setup_search_portable.sh" "$@"
