#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/network/setup_mac_portable.sh
exec "$(dirname "$0")/network/setup_mac_portable.sh" "$@"
