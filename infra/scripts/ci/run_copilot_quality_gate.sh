#!/usr/bin/env bash
# Copilot / RAG quality gate — run before release or after production fixes.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

echo "== Pytest: copilot + search + evidence =="
python -m pytest \
  tests/test_chat_intent.py \
  tests/test_chat_conversation.py \
  tests/test_evidence_orchestrator.py \
  tests/test_copilot_enhancements.py \
  tests/test_production_rag_fixes.py \
  tests/test_search_service.py \
  tests/test_auth_protected_routes.py \
  tests/test_security_authentication.py \
  -q

echo "== AI Lab Assistant eval (in-process) =="
python scripts/search/run_ai_lab_assistant_eval.py --role researcher

echo "== Continuous quality eval (search + retrieval + strategy sample) =="
OMEIA_CONTINUOUS_EVAL_ENABLED=true OMEIA_QUALITY_GATE_STRICT="${OMEIA_QUALITY_GATE_STRICT:-false}" \
  python scripts/ops/run_continuous_eval.py --force --skip-copilot

echo "Copilot quality gate passed."
