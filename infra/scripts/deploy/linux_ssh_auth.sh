#!/usr/bin/env bash
# Resolve Linux SSH auth: key-based (default) or interactive password.
# Source from deploy scripts; set OMEIA_LINUX_SSH_USE_PASSWORD=true in configs/.env to skip prompt.
#
# Usage:
#   source scripts/deploy/linux_ssh_auth.sh
#   linux_ssh_preflight "$LINUX_SSH"
#   linux_ssh_exec "$LINUX_SSH" "cd ~/data4TB/digital-notepad && git pull"

linux_ssh_preflight() {
  local host="${1:-}"
  [[ -z "$host" ]] && return 1

  if [[ "${OMEIA_LINUX_SSH_USE_PASSWORD:-}" == "true" ]]; then
    LINUX_SSH_BATCH="no"
    return 0
  fi
  if [[ "${OMEIA_LINUX_SSH_USE_PASSWORD:-}" == "false" ]]; then
    LINUX_SSH_BATCH="yes"
    return 0
  fi

  if ssh -o ConnectTimeout=6 -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$host" "echo ok" >/dev/null 2>&1; then
    LINUX_SSH_BATCH="yes"
    echo "SSH key auth OK for $host (no password needed)."
    return 0
  fi

  if [[ ! -t 0 ]]; then
    echo "ERROR: SSH to $host needs a password or SSH key, but this is not an interactive terminal."
    echo "  Fix: ssh-copy-id $host"
    echo "  Or set OMEIA_LINUX_SSH_USE_PASSWORD=true and run interactively (not for background daemons)."
    return 1
  fi

  echo ""
  echo "SSH to $host failed with key-based auth (BatchMode)."
  read -r -p "Does SSH to Linux need your login password? [y/N] " answer
  case "${answer,,}" in
    y|yes)
      LINUX_SSH_BATCH="no"
      echo "Using interactive SSH (you may be prompted for your Linux password)."
      echo "Tip: add OMEIA_LINUX_SSH_USE_PASSWORD=true to configs/.env to remember this."
      ;;
    *)
      LINUX_SSH_BATCH="yes"
      echo "Expecting SSH keys. Run once: ssh-copy-id $host"
      ;;
  esac
  return 0
}

linux_ssh_exec() {
  local host="$1"
  local remote_cmd="$2"
  local batch="${LINUX_SSH_BATCH:-yes}"
  local -a opts=(-o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new)
  if [[ "$batch" == "yes" ]]; then
    opts+=(-o BatchMode=yes)
  fi
  ssh "${opts[@]}" "$host" "$remote_cmd"
}
