#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/dev/docker_bootstrap.sh
exec "$(dirname "$0")/dev/docker_bootstrap.sh" "$@"
