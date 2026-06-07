#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/network/linux_tunnel_to_mac.sh
exec "$(dirname "$0")/network/linux_tunnel_to_mac.sh" "$@"
