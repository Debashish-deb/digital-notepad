#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/llm/generate_ollama_token.sh
exec "$(dirname "$0")/llm/generate_ollama_token.sh" "$@"
