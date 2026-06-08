#!/usr/bin/env bash
# Vite 8 requires Node >= 20.19 or >= 22.12. Cubbli ships 20.11 — use nvm when available.
set -euo pipefail

_die() {
  echo "$@" >&2
  (return 1 2>/dev/null) || exit 1
}

_node_ok() {
  command -v node >/dev/null 2>&1 || return 1
  node -e 'const v=process.versions.node.split(".").map(Number); const ok=(v[0]>22||(v[0]===22&&v[1]>=12)||(v[0]===20&&v[1]>=19)); process.exit(ok?0:1)' 2>/dev/null
}

if _node_ok; then
  (return 0 2>/dev/null) || exit 0
fi

if [[ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]]; then
  # shellcheck disable=SC1091
  . "${NVM_DIR:-$HOME/.nvm}/nvm.sh"
  if ! nvm use 22 2>/dev/null; then
    echo "Installing Node.js 22 via nvm (Vite 8 requires >=20.19 or >=22.12)..."
    nvm install 22
    nvm use 22
  fi
fi

if _node_ok; then
  echo "Using Node $(node -v) for Vite"
  (return 0 2>/dev/null) || exit 0
fi

_die "ERROR: Node $(node -v 2>/dev/null || echo missing) is too old for Vite 8.

On Linux (one-time):
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  source ~/.nvm/nvm.sh
  nvm install 22
  nvm use 22
  cd app_skeleton/ui/react_frontend && npm install
  ./scripts/start_linux.sh"
