#!/usr/bin/env bash
# Move lab catalog payloads from frontend public/ to server-side data/lab_catalog/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SRC="$ROOT/web/public/database"
DEST="$ROOT/omeia/data/lab_catalog"

if [ ! -d "$SRC" ]; then
  echo "No public/database to migrate."
  exit 0
fi

mkdir -p "$DEST/docs"
if [ -f "$SRC/catalog.json" ] && [ ! -f "$DEST/catalog.json" ]; then
  cp "$SRC/catalog.json" "$DEST/catalog.json"
  echo "Copied catalog.json -> $DEST/catalog.json"
fi

if [ -d "$SRC/docs" ]; then
  count="$(find "$SRC/docs" -name '*.json' | wc -l | tr -d ' ')"
  if [ "$count" -gt 0 ]; then
    rsync -a "$SRC/docs/" "$DEST/docs/"
    echo "Synced $count catalog doc JSON files -> $DEST/docs/"
  fi
fi

echo "Done. API serves from LAB_CATALOG_JSON / LAB_CATALOG_DOCS_DIR (defaults: $DEST)."
echo "Optional: remove $SRC after verifying /api/database/catalog works."
