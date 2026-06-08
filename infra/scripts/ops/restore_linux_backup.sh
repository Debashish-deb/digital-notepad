#!/usr/bin/env bash
# Restore OMEIA Linux backup — DESTRUCTIVE. Requires explicit confirmation.
#
# Usage:
#   bash scripts/ops/restore_linux_backup.sh /path/to/backup        # dry-run (default)
#   bash scripts/ops/restore_linux_backup.sh /path/to/backup --confirm-restore
#
# DANGER: --confirm-restore will overwrite the Postgres database and may replace Qdrant data.
# Stop the API and ingestion jobs before restoring.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR=""
CONFIRM=false

for arg in "$@"; do
  case "$arg" in
    --confirm-restore) CONFIRM=true ;;
    -h|--help)
      echo "Usage: $0 BACKUP_DIR [--confirm-restore]"
      echo "Without --confirm-restore this script only prints planned actions."
      exit 0
      ;;
    *)
      if [[ -z "$BACKUP_DIR" ]]; then
        BACKUP_DIR="$arg"
      fi
      ;;
  esac
done

if [[ -z "$BACKUP_DIR" || ! -d "$BACKUP_DIR" ]]; then
  echo "ERROR: provide an existing backup directory."
  exit 1
fi

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
fi

POSTGRES_CONN="${POSTGRES_CONN:-postgresql://farkki:farkki_dev_password@127.0.0.1:5432/farkki_ai}"
QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}"

PG_DUMP="$BACKUP_DIR/postgres/farkki_ai.sql.gz"
QDRANT_DIR="$BACKUP_DIR/qdrant"

echo "=== OMEIA restore plan ==="
echo "  Backup: $BACKUP_DIR"
echo "  Confirm: $CONFIRM"
echo ""
echo "Planned actions:"
if [[ -f "$PG_DUMP" ]]; then
  echo "  1. Restore Postgres from $PG_DUMP (OVERWRITES current DB)"
else
  echo "  1. SKIP Postgres — dump not found"
fi
if [[ -d "$QDRANT_DIR" ]]; then
  echo "  2. Qdrant snapshots in $QDRANT_DIR — manual/API restore required per collection"
else
  echo "  2. SKIP Qdrant — no snapshot dir"
fi
echo "  3. Config templates in $BACKUP_DIR/configs (never auto-overwrites configs/.env)"

if [[ "$CONFIRM" != true ]]; then
  echo ""
  echo "DRY-RUN ONLY. Re-run with --confirm-restore to execute Postgres restore."
  echo "Before restoring: stop API (uvicorn), processor daemon, and docker compose if needed."
  exit 0
fi

echo ""
echo "WARNING: restoring in 5 seconds — Ctrl+C to abort"
sleep 5

if [[ -f "$PG_DUMP" ]]; then
  if ! command -v psql >/dev/null 2>&1 || ! command -v gunzip >/dev/null 2>&1; then
    echo "ERROR: psql and gunzip required for Postgres restore"
    exit 1
  fi
  echo "Restoring Postgres..."
  gunzip -c "$PG_DUMP" | psql "$POSTGRES_CONN"
  echo "Postgres restore finished."
fi

echo "Qdrant restore: upload snapshots via Qdrant API or restore docker volume from ops backup."
echo "See backup manifest: $BACKUP_DIR/manifest.txt"
echo "Restore script finished (configs/.env unchanged)."
