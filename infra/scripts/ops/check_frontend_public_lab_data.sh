#!/usr/bin/env bash
# Fail CI/build when sensitive lab document payloads are bundled in frontend public/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PUBLIC="$ROOT/apps/web/public"
MAX_JSON_KB="${OMEIA_PUBLIC_JSON_MAX_KB:-512}"
FAIL=0

check_glob() {
  local pattern="$1"
  local label="$2"
  local matches
  matches="$(find "$PUBLIC" -path "$pattern" 2>/dev/null || true)"
  if [ -n "$matches" ]; then
    echo "ERROR: $label found under public/ (must be served via authenticated API):"
    echo "$matches" | head -20
    FAIL=1
  fi
}

check_glob "*/database/docs/*.json" "extracted document JSON"
check_glob "*/database/docs/*" "database/docs tree"

while IFS= read -r -d '' file; do
  size_kb=$(( $(stat -f%z "$file" 2>/dev/null || stat -c%s "$file") / 1024 ))
  if [ "$size_kb" -gt "$MAX_JSON_KB" ]; then
    echo "ERROR: oversized public JSON (${size_kb}KB > ${MAX_JSON_KB}KB): $file"
    FAIL=1
  fi
done < <(find "$PUBLIC/processed" -name '*.json' -type f -print0 2>/dev/null || true)

if [ "$FAIL" -ne 0 ]; then
  echo ""
  echo "Remediation: serve lab twins via /api/database/processed/* and document-library preview/export."
  echo "Remove large extracted payloads from app_skeleton/ui/react_frontend/public/ before production deploy."
  exit 1
fi

echo "OK: no blocked public lab-data paths; processed JSON within ${MAX_JSON_KB}KB limit."
