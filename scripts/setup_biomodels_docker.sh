#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/docker/setup_biomodels_docker.sh
exec "$(dirname "$0")/docker/setup_biomodels_docker.sh" "$@"
