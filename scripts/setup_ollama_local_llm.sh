#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/llm/setup_ollama_local_llm.sh
exec "$(dirname "$0")/llm/setup_ollama_local_llm.sh" "$@"
