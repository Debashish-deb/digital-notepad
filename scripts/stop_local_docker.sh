#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/dev/stop_local_docker.sh
exec "$(dirname "$0")/dev/stop_local_docker.sh" "$@"
