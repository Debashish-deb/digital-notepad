#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/check/check_docker.sh
exec "$(dirname "$0")/check/check_docker.sh" "$@"
