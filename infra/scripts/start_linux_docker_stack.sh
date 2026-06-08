#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/docker/start_linux_docker_stack.sh
exec "$(dirname "$0")/docker/start_linux_docker_stack.sh" "$@"
