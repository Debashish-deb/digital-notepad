#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/document-library/setup_research_knowledge.sh
exec "$(dirname "$0")/document-library/setup_research_knowledge.sh" "$@"
