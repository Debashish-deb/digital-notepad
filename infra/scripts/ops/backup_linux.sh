#!/usr/bin/env bash
# Backup Postgres, Qdrant snapshots, and non-secret configs for Linux workstation.
#
# Usage:
#   bash scripts/ops/backup_linux.sh --dry-run
#   bash scripts/ops/backup_linux.sh --output /path/to/backups/omeia-2026-06-06
#
# Safe by default: never prints or copies raw secret values from configs/.env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DRY_RUN=false
OUTPUT=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --output=*) OUTPUT="${arg#*=}" ;;
    --output)
      shift
      OUTPUT="${1:-}"
      ;;
    -h|--help)
      echo "Usage: $0 [--dry-run] [--output DIR]"
      exit 0
      ;;
  esac
done

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT="${OUTPUT:-$ROOT/backups/omeia-$STAMP}"
POSTGRES_CONN="${POSTGRES_CONN:-postgresql://farkki:farkki_dev_password@127.0.0.1:5432/farkki_ai}"
QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}"

run() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] $*"
  else
    echo "+ $*"
    "$@"
  fi
}

mkdir_safe() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] mkdir -p $1"
  else
    mkdir -p "$1"
  fi
}

echo "=== OMEIA Linux backup ==="
echo "  Output: $OUTPUT"
echo "  Dry run: $DRY_RUN"

mkdir_safe "$OUTPUT/postgres"
mkdir_safe "$OUTPUT/qdrant"
mkdir_safe "$OUTPUT/configs"

PG_FILE="$OUTPUT/postgres/farkki_ai.sql.gz"
if command -v pg_dump >/dev/null 2>&1; then
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] pg_dump | gzip > $PG_FILE"
  else
    pg_dump "$POSTGRES_CONN" | gzip > "$PG_FILE"
    echo "  Postgres dump: $PG_FILE ($(du -h "$PG_FILE" | awk '{print $1}'))"
  fi
else
  echo "WARN: pg_dump not found — skipping Postgres backup"
fi

if command -v curl >/dev/null 2>&1; then
  COLLECTIONS="$(curl -sf "$QDRANT_URL/collections" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(' '.join(c['name'] for c in d.get('result',{}).get('collections',[])))" 2>/dev/null || true)"
  if [[ -z "${COLLECTIONS:-}" ]]; then
    echo "WARN: no Qdrant collections discovered at $QDRANT_URL"
  else
    for coll in $COLLECTIONS; do
      SNAP_URL="$QDRANT_URL/collections/$coll/snapshots"
      if [[ "$DRY_RUN" == true ]]; then
        echo "[dry-run] curl -X POST $SNAP_URL"
      else
        curl -sf -X POST "$SNAP_URL" -H 'Content-Type: application/json' -d '{}' -o "$OUTPUT/qdrant/${coll}.snapshot.json" || echo "WARN: snapshot failed for $coll"
      fi
    done
  fi
else
  echo "WARN: curl not found — skipping Qdrant snapshots"
fi

REDacted="$OUTPUT/configs/env.redacted"
MANIFEST="$OUTPUT/manifest.txt"
if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] copy docker-compose.yml, configs/.env.example, linux-workstation.env.template"
  echo "[dry-run] redact configs/.env -> $REDacted"
else
  cp "$ROOT/docker-compose.yml" "$OUTPUT/configs/"
  cp "$ROOT/configs/.env.example" "$OUTPUT/configs/" 2>/dev/null || true
  cp "$ROOT/configs/linux-workstation.env.template" "$OUTPUT/configs/" 2>/dev/null || true
  if [[ -f "$ROOT/configs/.env" ]]; then
    grep -Ev '^(#|$$)' "$ROOT/configs/.env" \
      | grep -Eiv '(PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE|SERVICE_ROLE|CREDENTIAL)' \
      > "$REDacted" || true
  fi
  {
    echo "created_at=$STAMP"
    echo "repo=$ROOT"
    echo "postgres_conn_host=$(echo "$POSTGRES_CONN" | sed -E 's#.*@([^:/]+).*#\1#')"
    echo "qdrant_url=$QDRANT_URL"
    echo "dry_run=false"
  } > "$MANIFEST"
fi

echo "Backup complete."
