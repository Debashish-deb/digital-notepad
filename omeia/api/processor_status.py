"""Read autonomous processor state from disk (no auth — health-level public)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from omeia.api.data_layout import processor_pid_path, processor_state_path

STATE_PATH = processor_state_path()
PID_PATH = processor_pid_path()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    else:
        return True


def read_processor_status() -> dict[str, Any]:
    pid: int | None = None
    running = False
    if PID_PATH.is_file():
        try:
            pid = int(PID_PATH.read_text(encoding="utf-8").strip().splitlines()[0])
            running = _pid_alive(pid)
        except (ValueError, OSError):
            pid = None

    state: dict[str, Any] = {}
    if STATE_PATH.is_file():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            state = {"parse_error": True}

    return {
        "status": "running" if running else "stopped",
        "pid": pid,
        "pid_file": str(PID_PATH),
        "state_file": str(STATE_PATH),
        "mode": state.get("mode"),
        "last_step": state.get("last_step"),
        "last_run_at": state.get("last_run_at"),
        "runs_completed": state.get("runs_completed"),
        "interval_sec": state.get("interval_sec"),
        "steps": state.get("steps"),
        "errors": (state.get("errors") or [])[-5:],
        "started_at": state.get("started_at"),
        "updated_at": state.get("updated_at"),
    }
