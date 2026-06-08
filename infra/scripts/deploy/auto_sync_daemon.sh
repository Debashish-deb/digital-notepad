#!/usr/bin/env bash
# OMEIA Mac ↔ Linux auto-sync via ping + git (no rsync).
#
# Linux (recommended — keeps workstation up to date after Mac git push):
#   ./scripts/deploy/auto_sync_daemon.sh
#   OMEIA_AUTO_SYNC_INTERVAL_SEC=60 ./scripts/deploy/auto_sync_daemon.sh
#
# Mac (push local commits when Linux is reachable):
#   ./scripts/deploy/auto_sync_daemon.sh --mac-push
#
# One-shot pull on Linux:
#   ./scripts/deploy/auto_sync_daemon.sh --once
#
set -euo pipefail

_DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$_DEPLOY_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
[[ -z "$ROOT" ]] && ROOT="$(cd "$_DEPLOY_DIR/../.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
fi

INTERVAL="${OMEIA_AUTO_SYNC_INTERVAL_SEC:-90}"
PING_HOST="${OMEIA_AUTO_SYNC_PING_HOST:-}"
LOG_FILE="${OMEIA_AUTO_SYNC_LOG:-$ROOT/omeia/data/auto_sync_last_run.json}"
BRANCH="${OMEIA_AUTO_SYNC_BRANCH:-}"
MAC_PUSH=false
ONCE=false
DAEMON_LOOP=false

for arg in "$@"; do
  case "$arg" in
    --mac-push) MAC_PUSH=true ;;
    --once) ONCE=true ;;
    -h|--help)
      cat <<'EOF'
Usage:
  Linux daemon:  ./scripts/deploy/auto_sync_daemon.sh
  Mac push mode: ./scripts/deploy/auto_sync_daemon.sh --mac-push
  Single pull:   ./scripts/deploy/auto_sync_daemon.sh --once

Env (configs/.env):
  OMEIA_AUTO_SYNC_INTERVAL_SEC=90
  OMEIA_AUTO_SYNC_PING_HOST=100.80.231.55   # optional; default = git remote host
  TAILSCALE_LINUX_IP / LINUX_SSH            # Mac push mode
EOF
      exit 0
      ;;
  esac
done

mkdir -p "$(dirname "$LOG_FILE")"

_ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

_write_log() {
  local status="$1"
  local message="$2"
  shift 2
  OMEIA_SYNC_AT="$(_ts)" \
  OMEIA_SYNC_HOST="$(hostname -s 2>/dev/null || hostname)" \
  OMEIA_SYNC_PLATFORM="$(uname -s)" \
  OMEIA_SYNC_MODE="$([[ "$MAC_PUSH" == true ]] && echo mac_push || echo linux_pull)" \
  OMEIA_SYNC_STATUS="$status" \
  OMEIA_SYNC_MESSAGE="$message" \
  OMEIA_SYNC_LOG="$LOG_FILE" \
  python3 - "$@" <<'PY'
import json, os, sys
from pathlib import Path
extra = {}
for arg in sys.argv[1:]:
    if "=" not in arg:
        continue
    key, value = arg.split("=", 1)
    extra[key] = int(value) if value.isdigit() else value
payload = {
    "at": os.environ["OMEIA_SYNC_AT"],
    "host": os.environ["OMEIA_SYNC_HOST"],
    "platform": os.environ["OMEIA_SYNC_PLATFORM"],
    "mode": os.environ["OMEIA_SYNC_MODE"],
    "status": os.environ["OMEIA_SYNC_STATUS"],
    "message": os.environ["OMEIA_SYNC_MESSAGE"],
}
payload.update(extra)
path = Path(os.environ["OMEIA_SYNC_LOG"])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
PY
}

_resolve_branch() {
  if [[ -n "$BRANCH" ]]; then
    echo "$BRANCH"
    return
  fi
  git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --abbrev-ref HEAD
}

_ping_ok() {
  local host="$1"
  if [[ -z "$host" ]]; then
    return 0
  fi
  if ping -c 1 -W 2 "$host" >/dev/null 2>&1; then
    return 0
  fi
  # macOS ping uses -W milliseconds; Linux uses seconds — try both
  ping -c 1 -t 2 "$host" >/dev/null 2>&1
}

_git_remote_host() {
  local url
  url="$(git remote get-url origin 2>/dev/null || true)"
  [[ -z "$url" ]] && return 0
  python3 - <<'PY' "$url"
import sys
from urllib.parse import urlparse
raw = sys.argv[1].strip()
if raw.startswith("git@"):
    print(raw.split(":", 1)[0].split("@", 1)[-1])
elif "://" in raw:
    print(urlparse(raw).hostname or "")
else:
    print("")
PY
}

_linux_pull_once() {
  local branch ping_target remote_host behind
  branch="$(_resolve_branch)"
  remote_host="$(_git_remote_host)"
  ping_target="${PING_HOST:-$remote_host}"

  if [[ -n "$ping_target" ]] && ! _ping_ok "$ping_target"; then
    _write_log "skipped" "Ping failed — network or host unreachable" "ping_host=$ping_target" "branch=$branch"
    return 0
  fi

  if ! git fetch origin "$branch" 2>/dev/null; then
    git fetch origin 2>/dev/null || true
  fi

  behind="$(git rev-list --count HEAD..origin/"$branch" 2>/dev/null || echo 0)"
  if [[ "${behind:-0}" -eq 0 ]]; then
    _write_log "ok" "Already up to date" "branch=$branch" "commits_behind=0" "ping_host=$ping_target"
    return 0
  fi

  echo "[$(_ts)] Pulling $behind commit(s) on $branch…"
  git pull --ff-only origin "$branch"
  if [[ -f "$ROOT/scripts/ops/linux_post_pull.sh" ]]; then
    OMEIA_POST_PULL_SKIP_READY=true \
      bash "$ROOT/scripts/ops/linux_post_pull.sh" 2>/dev/null || \
      echo "WARN: post-pull deps step failed (non-fatal)"
  fi
  _write_log "pulled" "Fast-forwarded $behind commit(s)" "branch=$branch" "commits_behind=$behind" "ping_host=$ping_target"
}

_mac_push_once() {
  local linux_ssh ping_target linux_ip branch ahead

  linux_ssh="${LINUX_SSH:-${OLLAMA_LINUX_SSH:-}}"
  linux_ip="${TAILSCALE_LINUX_IP:-}"
  if [[ -z "$linux_ssh" && -n "${TAILSCALE_LINUX_HOST:-}" ]]; then
    linux_ssh="${LINUX_SSH_USER:-debdeba}@${TAILSCALE_LINUX_HOST}"
  elif [[ -z "$linux_ssh" && -n "$linux_ip" ]]; then
    linux_ssh="${LINUX_SSH_USER:-debdeba}@${linux_ip}"
  fi

  ping_target="${PING_HOST:-$linux_ip}"
  if [[ -z "$ping_target" && -n "$linux_ssh" ]]; then
    ping_target="${linux_ssh#*@}"
  fi

  if [[ -z "$linux_ssh" ]]; then
    _write_log "error" "Set LINUX_SSH or TAILSCALE_LINUX_IP in configs/.env" "hint=LINUX_SSH_or_TAILSCALE_LINUX_IP"
    return 1
  fi

  if [[ -n "$ping_target" ]] && ! _ping_ok "$ping_target"; then
    _write_log "skipped" "Linux unreachable (ping)" "ping_host=$ping_target" "linux_ssh=$linux_ssh"
    return 0
  fi

  branch="$(_resolve_branch)"
  ahead="$(git rev-list --count origin/"$branch"..HEAD 2>/dev/null || echo 0)"
  if [[ "${ahead:-0}" -gt 0 ]]; then
    echo "[$(_ts)] Pushing $ahead local commit(s)…"
    git push -u origin HEAD
  fi

  echo "[$(_ts)] Git pull on Linux ($linux_ssh)…"
  linux_ssh_exec "$linux_ssh" \
    "cd ${LINUX_REPO:-~/data4TB/digital-notepad} && git fetch origin && git pull --ff-only origin ${branch}"

  _write_log "synced" "Mac push + Linux pull complete" "branch=$branch" "commits_ahead=${ahead:-0}" "linux_ssh=$linux_ssh" "ping_host=$ping_target"
}

_run_cycle() {
  if [[ "$MAC_PUSH" == true ]]; then
    _mac_push_once
  else
    _linux_pull_once
  fi
}

# shellcheck source=linux_ssh_auth.sh
source "$_DEPLOY_DIR/linux_ssh_auth.sh"

echo "=== OMEIA auto-sync ==="
echo "  Repo:     $ROOT"
echo "  Mode:     $([[ "$MAC_PUSH" == true ]] && echo mac-push || echo linux-pull)"
echo "  Interval: ${INTERVAL}s"
echo "  Log:      $LOG_FILE"
echo ""

if [[ "$MAC_PUSH" == true ]]; then
  _linux_ssh="${LINUX_SSH:-${OLLAMA_LINUX_SSH:-}}"
  [[ -z "$_linux_ssh" && -n "${TAILSCALE_LINUX_HOST:-}" ]] && _linux_ssh="${LINUX_SSH_USER:-debdeba}@${TAILSCALE_LINUX_HOST}"
  [[ -z "$_linux_ssh" && -n "${TAILSCALE_LINUX_IP:-}" ]] && _linux_ssh="${LINUX_SSH_USER:-debdeba}@${TAILSCALE_LINUX_IP}"
  if [[ -n "$_linux_ssh" ]]; then
    linux_ssh_preflight "$_linux_ssh" || exit 1
    if [[ "${LINUX_SSH_BATCH:-yes}" == "no" && "$ONCE" != true ]]; then
      echo ""
      echo "WARN: Password SSH cannot run in a background loop."
      echo "  Use: ./scripts/deploy/auto_sync_daemon.sh --mac-push --once"
      echo "  Or: Linux-only pull daemon (no Mac SSH): ./scripts/deploy/auto_sync_daemon.sh"
      echo "  Or: ssh-copy-id $_linux_ssh  (recommended)"
      read -r -p "Continue anyway? You will be prompted every cycle. [y/N] " cont
      [[ "${cont,,}" == y || "${cont,,}" == yes ]] || exit 1
      DAEMON_LOOP=true
    fi
  fi
fi

if [[ "$ONCE" == true ]]; then
  _run_cycle
  exit 0
fi

while true; do
  _run_cycle || true
  sleep "$INTERVAL"
done
