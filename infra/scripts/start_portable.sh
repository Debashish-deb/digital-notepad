#!/usr/bin/env bash
# Backward-compat — routes to start_linux.sh or start_mac.sh by OS
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ "$(uname -s)" == "Linux" ]]; then
  exec "$ROOT/start_linux.sh" "$@"
fi
exec "$ROOT/start_mac.sh" "$@"
