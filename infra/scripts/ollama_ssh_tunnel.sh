#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/llm/ollama_ssh_tunnel.sh
exec "$(dirname "$0")/llm/ollama_ssh_tunnel.sh" "$@"
