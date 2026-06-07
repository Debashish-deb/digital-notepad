#!/usr/bin/env bash
# Start/stop OS-level autonomous processor (survives Cursor IDE / shell exit).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DATA_DIR="${REPO_ROOT}/app_skeleton/data"
PID_FILE="${DATA_DIR}/00_registry/processor.pid"
STATE_FILE="${DATA_DIR}/00_registry/processor_state.json"
LOG_FILE="${DATA_DIR}/04_runtime_logs/latest.log"
# Legacy fallbacks
[[ -f "${PID_FILE}" ]] || PID_FILE="${DATA_DIR}/processor.pid"
[[ -f "${STATE_FILE}" ]] || STATE_FILE="${DATA_DIR}/processor_state.json"
[[ -f "${LOG_FILE}" ]] || LOG_FILE="${DATA_DIR}/logs/autonomous_processor.log"

PYTHON="${PYTHON:-}"
if [[ -z "${PYTHON}" ]]; then
  if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON="${REPO_ROOT}/.venv/bin/python"
  elif [[ -x /opt/omeia/venv/bin/python ]]; then
    PYTHON="/opt/omeia/venv/bin/python"
  else
    PYTHON="$(command -v python3)"
  fi
fi

PROC_PY="${SCRIPT_DIR}/autonomous_processor.py"

usage() {
  echo "Usage: $0 {start|stop|status|once}"
  echo "  start  — nohup daemon (PROCESSOR_INTERVAL_SEC between cycles)"
  echo "  stop   — SIGTERM via processor.pid"
  echo "  status — pid file + processor_state.json summary"
  echo "  once   — single pipeline pass (foreground)"
}

read_pid() {
  if [[ -f "${PID_FILE}" ]]; then
    head -n1 "${PID_FILE}" | tr -d '[:space:]'
  fi
}

pid_running() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

cmd_start() {
  local pid
  pid="$(read_pid || true)"
  if pid_running "${pid:-}"; then
    echo "Already running (pid ${pid}). Use '$0 stop' first or autonomous_processor.py --force"
    exit 1
  fi
  mkdir -p "$(dirname "${LOG_FILE}")"
  cd "${REPO_ROOT}"
  nohup "${PYTHON}" "${PROC_PY}" --daemon >> "${LOG_FILE}" 2>&1 &
  disown -h %1 2>/dev/null || true
  sleep 1
  pid="$(read_pid || true)"
  if pid_running "${pid:-}"; then
    echo "Started autonomous processor (pid ${pid})"
    echo "Log: ${LOG_FILE}"
  else
    echo "Start may have failed — check ${LOG_FILE}"
    exit 1
  fi
}

cmd_stop() {
  cd "${REPO_ROOT}"
  "${PYTHON}" "${PROC_PY}" --stop
}

cmd_once() {
  cd "${REPO_ROOT}"
  exec "${PYTHON}" "${PROC_PY}" --once "$@"
}

cmd_status() {
  local pid state_line
  pid="$(read_pid || true)"
  if pid_running "${pid:-}"; then
    echo "running pid=${pid}"
  else
    echo "not running"
    [[ -n "${pid:-}" ]] && echo "(stale pid file: ${pid})"
  fi
  if [[ -f "${STATE_FILE}" ]]; then
    if command -v jq >/dev/null 2>&1; then
      jq '{mode, last_step, last_run_at, runs_completed, interval_sec: .interval_sec, errors: (.errors | .[-3:])}' \
        "${STATE_FILE}" 2>/dev/null || cat "${STATE_FILE}"
    else
      echo "state: ${STATE_FILE}"
      grep -E '"mode"|"last_step"|"last_run_at"|"runs_completed"' "${STATE_FILE}" 2>/dev/null || true
    fi
  else
    echo "no state file yet (${STATE_FILE})"
  fi
  [[ -f "${LOG_FILE}" ]] && echo "log: ${LOG_FILE} ($(wc -l < "${LOG_FILE}" | tr -d ' ') lines)"
}

case "${1:-}" in
  start) shift; cmd_start "$@" ;;
  stop) shift; cmd_stop "$@" ;;
  status) shift; cmd_status "$@" ;;
  once) shift; cmd_once "$@" ;;
  -h|--help|help) usage ;;
  *)
    usage
    exit 1
    ;;
esac
