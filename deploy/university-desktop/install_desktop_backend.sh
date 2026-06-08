#!/usr/bin/env bash
# Cross-platform OMEIA desktop backend setup: Linux (systemd prod) or macOS (launchd / dev).
set -euo pipefail

REPO_DEPLOY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${REPO_DEPLOY}/../.." && pwd)"
OS="$(uname -s)"

chmod +x "${REPO_DEPLOY}/run_api_dev.sh" "${REPO_DEPLOY}/scheduled_ingest.sh" 2>/dev/null || true
chmod +x "${REPO_ROOT}/scripts/ops/autonomous_processor.sh" 2>/dev/null || true

echo "==> OMEIA desktop backend install (${OS})"

install_python_deps() {
  local venv_path="$1"
  local owner="${2:-}"
  if [[ ! -d "${venv_path}" ]]; then
    echo "Creating venv at ${venv_path}"
    python3 -m venv "${venv_path}"
    if [[ -n "${owner}" ]]; then
      sudo chown -R "${owner}:${owner}" "${venv_path}"
    fi
  fi
  local pip="${venv_path}/bin/pip"
  if [[ -n "${owner}" ]]; then
    sudo -u "${owner}" "${pip}" install -U pip wheel
    sudo -u "${owner}" "${pip}" install -r "${REPO_ROOT}/omeia/api/requirements.txt"
    sudo -u "${owner}" "${pip}" install httpx pillow
  else
    "${pip}" install -U pip wheel
    "${pip}" install -r "${REPO_ROOT}/omeia/api/requirements.txt"
    "${pip}" install httpx pillow
  fi
}

ensure_env_template() {
  local dest="$1"
  local owner="${2:-}"
  mkdir -p "$(dirname "${dest}")"
  if [[ ! -f "${dest}" ]]; then
    cp "${REPO_DEPLOY}/.env.desktop.example" "${dest}"
    if [[ -n "${owner}" ]]; then
      sudo chown "${owner}:${owner}" "${dest}"
    fi
    echo "Created ${dest} — edit CORS_ORIGINS, mounts, auth."
  else
    echo "Keeping existing ${dest}"
  fi
}

install_linux() {
  local OMEIA_USER="${OMEIA_USER:-omeia}"
  local OMEIA_ROOT="${OMEIA_ROOT:-/opt/omeia/digital-notepad}"
  local OMEIA_VENV="${OMEIA_VENV:-/opt/omeia/venv}"
  local OMEIA_DEPLOY="${OMEIA_DEPLOY:-/opt/omeia/deploy/university-desktop}"

  if ! id -u "${OMEIA_USER}" &>/dev/null; then
    echo "Creating system user ${OMEIA_USER}"
    sudo useradd --system --home-dir /opt/omeia --shell /usr/sbin/nologin "${OMEIA_USER}" || true
  fi

  sudo mkdir -p /opt/omeia/secrets "${OMEIA_DEPLOY}"
  sudo chown -R "${OMEIA_USER}:${OMEIA_USER}" /opt/omeia

  if [[ ! -d "${OMEIA_ROOT}" ]]; then
    echo "NEEDS_USER_DECISION: clone repo to ${OMEIA_ROOT} before re-running."
    echo "  git clone <repo-url> ${OMEIA_ROOT}"
    exit 1
  fi

  install_python_deps "${OMEIA_VENV}" "${OMEIA_USER}"
  ensure_env_template "${OMEIA_DEPLOY}/.env" "${OMEIA_USER}"

  echo "Installing systemd units"
  for unit in omeia-api.service omeia-ingest.service omeia-ingest.timer omeia-processor.service; do
    sudo cp "${REPO_DEPLOY}/${unit}" "/etc/systemd/system/${unit}"
  done
  sudo systemctl daemon-reload
  sudo systemctl enable omeia-api.service omeia-ingest.timer omeia-processor.service

  echo ""
  echo "Linux production — next steps:"
  echo "  1. Edit ${OMEIA_DEPLOY}/.env (CORS_ORIGINS, PLATFORM_AUTH_DISABLED=false, Firebase, DataCloud)"
  echo "  2. Mount P-drive / lab storage (see .env.desktop.example)"
  echo "  3. sudo apt install -y python3-venv  # if needed"
  echo "  4. sudo systemctl start omeia-api.service"
  echo "  5. Caddy or nginx: Caddyfile.example / nginx-omeia.conf.example"
  echo "  6. Firewall: ufw-notes.md"
  echo "  7. sudo systemctl start omeia-ingest.timer"
}

install_macos() {
  local VENV="${OMEIA_VENV:-${REPO_ROOT}/.venv}"
  local ENV_FILE="${OMEIA_ENV:-${REPO_ROOT}/configs/.env}"

  install_python_deps "${VENV}" ""
  ensure_env_template "${ENV_FILE}" ""

  mkdir -p "${REPO_ROOT}/logs"
  local PLIST_SRC="${REPO_DEPLOY}/launchd/com.app_skeleton.api.plist"
  local PLIST_DEST="${HOME}/Library/LaunchAgents/com.app_skeleton.api.plist"

  if [[ -f "${PLIST_SRC}" ]]; then
    sed \
      -e "s|REPLACE_WITH_REPO_ROOT|${REPO_ROOT}|g" \
      -e "s|REPLACE_WITH_VENV|${VENV}|g" \
      "${PLIST_SRC}" > "${PLIST_DEST}"
    echo "Wrote ${PLIST_DEST}"
  fi

  echo ""
  echo "macOS dev/test — next steps:"
  echo "  1. Edit ${ENV_FILE} (CORS_ORIGINS=http://localhost:5173, PLATFORM_AUTH_DISABLED=true)"
  echo "  2. Mount volumes under /Volumes/... if using PDRIVE / LAB_STORAGE_ROOT"
  echo "  3. Quick run: ${REPO_DEPLOY}/run_api_dev.sh"
  echo "  4. Optional auto-start:"
  echo "       launchctl load ${PLIST_DEST}"
  echo "       launchctl start com.app_skeleton.api"
  echo "  5. Optional TLS: brew install caddy && edit Caddyfile.example"
  echo "  6. Scheduled ingest: ${REPO_DEPLOY}/scheduled_ingest.sh (or launchd/cron)"
  echo ""
  echo "Bind 127.0.0.1:8000 for dev (default in run_api_dev.sh). pf / firewall optional."
}

case "${OS}" in
  Linux)
    install_linux
    ;;
  Darwin)
    install_macos
    ;;
  *)
    echo "Unsupported OS: ${OS}. Use run_api_dev.sh manually on this platform."
    exit 1
    ;;
esac

echo "Done."
