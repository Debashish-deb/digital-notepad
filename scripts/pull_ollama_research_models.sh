#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/llm/pull_ollama_research_models.sh
exec "$(dirname "$0")/llm/pull_ollama_research_models.sh" "$@"
