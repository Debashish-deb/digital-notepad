#!/usr/bin/env bash
# Vite 8 requires Node >= 20.19 or >= 22.12. Pin nvm to 22.14.0 (not generic "22").
# Sourced from start.sh — must NOT use "return" (that exits the parent start.sh).
set -euo pipefail

VITE_MIN_NODE="${VITE_MIN_NODE:-22.14.0}"

_die() {
  echo "$@" >&2
  exit 1
}

_node_ok() {
  command -v node >/dev/null 2>&1 || return 1
  node -e 'const p=process.versions.node.split(".").map(Number);const m=p[0]||0,n=p[1]||0;process.exit(m>22||(m===22&&n>=12)||(m===20&&n>=19)?0:1)'
}

_activate_nvm_node() {
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  [[ -s "$NVM_DIR/nvm.sh" ]] || return 1
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
  if ! nvm use "$VITE_MIN_NODE" >/dev/null 2>&1; then
    echo "Installing Node.js ${VITE_MIN_NODE} via nvm (Vite 8 requires >=20.19 or >=22.12)..."
    nvm install "$VITE_MIN_NODE"
    nvm use "$VITE_MIN_NODE"
  fi
  nvm alias default "$VITE_MIN_NODE" 2>/dev/null || true
  hash -r
  export PATH="${NVM_DIR}/versions/node/v${VITE_MIN_NODE}/bin:${PATH}"
}

_activate_nvm_node || true

if ! _node_ok; then
  _die "ERROR: Node $(node -v 2>/dev/null || echo missing) is too old for Vite 8 (need >=20.19 or >=22.12).

Fix:
  export NVM_DIR=\"\$HOME/.nvm\" && . \"\$NVM_DIR/nvm.sh\"
  nvm install ${VITE_MIN_NODE} && nvm use ${VITE_MIN_NODE}
  nvm alias default ${VITE_MIN_NODE}
  cd web && npm install
  ./scripts/start_linux.sh"
fi

echo "Using Node $(node -v) for Vite"
