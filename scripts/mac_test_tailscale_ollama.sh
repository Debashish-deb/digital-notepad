#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/network/mac_test_tailscale_ollama.sh
exec "$(dirname "$0")/network/mac_test_tailscale_ollama.sh" "$@"
