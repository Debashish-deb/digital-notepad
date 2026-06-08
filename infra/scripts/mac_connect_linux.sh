#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/network/mac_connect_linux.sh
exec "$(dirname "$0")/network/mac_connect_linux.sh" "$@"
