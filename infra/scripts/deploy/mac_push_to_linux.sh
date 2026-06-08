#!/usr/bin/env bash
# Mac → Linux: push git + rsync heavy data (OMEIA-database, optional bundles).
#
# Usage (on Mac):
#   export LINUX_SSH=labuser@100.80.231.55   # Tailscale IP of Linux workstation
#   ./scripts/deploy/mac_push_to_linux.sh
#   ./scripts/deploy/mac_push_to_linux.sh --data-only
#   ./scripts/deploy/mac_push_to_linux.sh --code-only
# SSH/rsync steps require key-based auth on the Linux host first:
#   ssh-copy-id labuser@<linux-tailscale-ip>
#
set -euo pipefail

_DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$_DEPLOY_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$ROOT" ]]; then
  ROOT="$(cd "$_DEPLOY_DIR/../../.." && pwd)"
fi
cd "$ROOT"

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
fi

# Prefer Tailscale machine name (Tailscale SSH) then IP from configs/.env
LINUX_SSH="${LINUX_SSH:-${OLLAMA_LINUX_SSH:-}}"
if [[ -z "$LINUX_SSH" && -n "${TAILSCALE_LINUX_HOST:-}" ]]; then
  LINUX_SSH="${LINUX_SSH_USER:-labuser}@${TAILSCALE_LINUX_HOST}"
elif [[ -z "$LINUX_SSH" && -n "${TAILSCALE_LINUX_IP:-}" ]]; then
  LINUX_SSH="${LINUX_SSH_USER:-labuser}@${TAILSCALE_LINUX_IP}"
fi
LINUX_REPO="${LINUX_REPO:-~/data4TB/digital-notepad}"
LINUX_DATA="${LINUX_DATA:-~/data4TB/OMEIA-database}"

CODE_ONLY=false
DATA_ONLY=false
GIT_ONLY=false
DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --code-only) CODE_ONLY=true ;;
    --data-only) DATA_ONLY=true ;;
    --git-only) GIT_ONLY=true; CODE_ONLY=true ;;
    --dry-run) DRY_RUN=true ;;
    -h|--help)
      echo "Usage: LINUX_SSH=user@host $0 [--git-only|--code-only|--data-only|--dry-run]"
      echo ""
      echo "  --git-only   git push only; no SSH (run git pull on Linux yourself)"
      echo "  --code-only  git push + ssh git pull on Linux"
      echo "  --data-only  rsync OMEIA-database only"
      exit 0
      ;;
  esac
done

if [[ "$GIT_ONLY" != true && -z "$LINUX_SSH" ]]; then
  echo "ERROR: set LINUX_SSH=labuser@<linux-tailscale-ip>"
  echo "  Or use --git-only (no SSH) and run git pull on Linux yourself"
  exit 1
fi

# shellcheck source=linux_ssh_auth.sh
source "$_DEPLOY_DIR/linux_ssh_auth.sh"
if [[ "$GIT_ONLY" != true && -n "$LINUX_SSH" ]]; then
  linux_ssh_preflight "$LINUX_SSH" || exit 1
fi

RSYNC_FLAGS=(-avz --progress)
[[ "$DRY_RUN" == true ]] && RSYNC_FLAGS+=(--dry-run)

# Explicit Mac source wins; DATABASE_ROOT in configs/.env is often the Linux path after copy-paste.
MAC_DATABASE="${MAC_DATABASE_ROOT:-${DATABASE_ROOT:-$ROOT/../OMEIA-database}}"
MAC_DATABASE="$(cd "$MAC_DATABASE" 2>/dev/null && pwd || echo "$MAC_DATABASE")"

if [[ "$(uname -s)" != "Darwin" && "$DATA_ONLY" == true ]]; then
  echo "ERROR: --data-only must run on your Mac (source = Mac OMEIA-database)."
  echo "  You are on: $(uname -n) ($(uname -s))"
  echo "  Detected source: $MAC_DATABASE"
  echo ""
  echo "On Mac, run:"
  echo "  export LINUX_SSH=labuser@100.80.231.55"
  echo "  export MAC_DATABASE_ROOT=/path/to/OMEIA-database"
  echo "  ./scripts/deploy/mac_push_to_linux.sh --data-only"
  exit 1
fi

if [[ "$MAC_DATABASE" == /home/* ]]; then
  echo "WARN: Mac source looks like a Linux path: $MAC_DATABASE"
  echo "      Set MAC_DATABASE_ROOT to your Mac folder, e.g.:"
  echo "      export MAC_DATABASE_ROOT=/path/to/OMEIA-database"
  if [[ "$DATA_ONLY" == true ]]; then
    exit 1
  fi
fi

echo "=== Mac → Linux deploy ==="
echo "  SSH:      $LINUX_SSH"
echo "  Repo:     $LINUX_REPO"
echo "  Data:     $LINUX_DATA"
echo "  Mac DB:   $MAC_DATABASE"
echo ""

if [[ "$DATA_ONLY" != true ]]; then
  echo "--- Git push (Mac) ---"
  git push -u origin HEAD
  echo ""
  if [[ "$GIT_ONLY" == true ]]; then
    echo "--- Skipping SSH ( --git-only ) ---"
    echo "On Linux, run:"
    echo "  cd $LINUX_REPO && git pull"
  else
    echo "--- Git pull on Linux ---"
    linux_ssh_exec "$LINUX_SSH" "cd $LINUX_REPO && git pull"
  fi
  echo ""
fi

if [[ "$CODE_ONLY" != true && "$GIT_ONLY" != true ]]; then
  if [[ ! -d "$MAC_DATABASE" ]]; then
    echo "WARN: Mac DATABASE_ROOT not found: $MAC_DATABASE"
    echo "      Skip data rsync or set DATABASE_ROOT in configs/.env"
  else
    echo "--- Rsync OMEIA-database (heavy — may take a long time) ---"
    linux_ssh_exec "$LINUX_SSH" "mkdir -p $LINUX_DATA"
    rsync "${RSYNC_FLAGS[@]}" \
      --exclude '.DS_Store' \
      --exclude '**/.Trash/**' \
      "$MAC_DATABASE/" "$LINUX_SSH:$LINUX_DATA/"
    echo ""
  fi

  # Optional: lab member avatars / large assets outside database root
  if [[ -d "$ROOT/labMember" ]]; then
    echo "--- Rsync labMember assets ---"
    rsync "${RSYNC_FLAGS[@]}" "$ROOT/labMember/" "$LINUX_SSH:$LINUX_REPO/labMember/"
  fi
fi

echo "=== Done ==="
echo "On Linux, run full bootstrap:"
echo "  ssh $LINUX_SSH"
echo "  cd $LINUX_REPO && ./scripts/deploy/linux_bootstrap_all.sh"
