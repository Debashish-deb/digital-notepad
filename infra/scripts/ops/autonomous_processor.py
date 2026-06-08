#!/usr/bin/env python3
"""OS-level autonomous processor: vault ingest, digitalization, Supabase sync.

Runs independently of Cursor IDE or any agent session. Use autonomous_processor.sh
or systemd/launchd units to start/stop.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "configs" / ".env")
load_dotenv(ROOT / "deploy" / "university-desktop" / ".env")
load_dotenv()

from app_skeleton.api.data_layout import (  # noqa: E402
    processor_pid_path,
    processor_state_path,
    runtime_log_write_path,
)

DATA_DIR = ROOT / "omeia" / "data"
STATE_PATH = processor_state_path()
PID_PATH = processor_pid_path()
LOG_PATH = runtime_log_write_path("autonomous_processor.log")

_SHUTDOWN = False
_LOGGER: logging.Logger | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _setup_logging() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("autonomous_processor")
    logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger


def _load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _utc_now()
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_pid_file() -> int | None:
    if not PID_PATH.is_file():
        return None
    try:
        raw = PID_PATH.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        return int(raw)
    except (ValueError, OSError):
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    else:
        return True


def _write_pid_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(f"{os.getpid()}\n", encoding="utf-8")


def _remove_pid_file() -> None:
    try:
        PID_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def _acquire_lock(*, force: bool) -> None:
    existing = _read_pid_file()
    if existing is not None and _pid_alive(existing) and existing != os.getpid():
        if not force:
            raise SystemExit(
                f"Another autonomous processor is running (pid {existing}). "
                "Use --force to replace or --stop to terminate it."
            )
        try:
            os.kill(existing, signal.SIGTERM)
            time.sleep(2)
        except ProcessLookupError:
            pass
    _write_pid_file()


def _parse_steps() -> list[str]:
    raw = os.getenv("PROCESSOR_STEPS", "vault,digitalize,supabase_sync").strip()
    aliases = {"supabase": "supabase_sync"}
    steps: list[str] = []
    for part in raw.split(","):
        name = aliases.get(part.strip().lower(), part.strip().lower())
        if name and name not in steps:
            steps.append(name)
    return steps or ["vault", "digitalize", "supabase_sync"]


def _interval_sec() -> int:
    try:
        return max(60, int(os.getenv("PROCESSOR_INTERVAL_SEC", "3600")))
    except ValueError:
        return 3600


def _max_files() -> int | None:
    raw = os.getenv("PROCESSOR_MAX_FILES", "").strip()
    if not raw:
        return None
    try:
        return max(1, int(raw))
    except ValueError:
        return None


def _vault_roots() -> list[Path]:
    from app_skeleton.api.paths import DATABASE_ROOT, lab_storage_root

    roots: list[Path] = []
    for candidate in (DATABASE_ROOT, lab_storage_root()):
        if candidate is None:
            continue
        resolved = candidate.resolve()
        if resolved.is_dir() and resolved not in roots:
            roots.append(resolved)
    return roots


def _step_vault(*, resume: bool, state: dict[str, Any]) -> dict[str, Any]:
    from app_skeleton.api.vault_ingestion_engine import run_ingest_scan

    logger = _LOGGER or logging.getLogger("autonomous_processor")
    results: list[dict[str, Any]] = []
    roots = _vault_roots()
    if not roots:
        out = {"status": "skipped", "reason": "no_vault_scan_root"}
        logger.warning("Vault step skipped: DATABASE_ROOT and LAB_STORAGE_ROOT unset or missing")
        return out

    max_files = _max_files()
    for scan_root in roots:
        logger.info("Vault ingest scan root=%s resume=%s", scan_root, resume)
        try:
            result = run_ingest_scan(
                scan_root=scan_root,
                resume=resume,
                max_files=max_files,
            )
            results.append({"scan_root": str(scan_root), **result})
        except Exception as exc:
            logger.exception("Vault scan failed for %s", scan_root)
            results.append({"scan_root": str(scan_root), "status": "error", "detail": str(exc)})

    state["checkpoint"] = {"vault": {"roots": [str(r) for r in roots], "resume": resume}}
    status = "error" if any(r.get("status") == "error" for r in results) else "ok"
    return {"status": status, "roots": results}


def _step_digitalize(*, resume: bool, state: dict[str, Any]) -> dict[str, Any]:
    from app_skeleton.api.project_digitalization_engine import run_digitalization

    logger = _LOGGER or logging.getLogger("autonomous_processor")
    logger.info("Digitalization full scan resume=%s", resume)
    try:
        result = run_digitalization(
            mode="full",
            resume=resume,
            max_files=_max_files(),
        )
        state["checkpoint"] = {**(state.get("checkpoint") or {}), "digitalize": {"resume": resume}}
        return {"status": "ok", **result}
    except Exception as exc:
        logger.exception("Digitalization failed")
        return {"status": "error", "detail": str(exc)}


def _step_supabase_sync() -> dict[str, Any]:
    from app_skeleton.api.supabase_sync import (
        supabase_hosted_password_set,
        supabase_sync_enabled,
        sync_documents_to_supabase,
    )

    logger = _LOGGER or logging.getLogger("autonomous_processor")
    if not supabase_sync_enabled():
        return {"status": "skipped", "reason": "SUPABASE_SYNC_ENABLED=false"}
    if not supabase_hosted_password_set():
        return {"status": "skipped", "reason": "SUPABASE_DB_PASSWORD unset"}
    try:
        return sync_documents_to_supabase(dry_run=False)
    except Exception as exc:
        logger.exception("Supabase sync failed")
        return {"status": "error", "detail": str(exc)}


def _run_pipeline(*, resume: bool, state: dict[str, Any]) -> dict[str, Any]:
    steps = _parse_steps()
    run_report: dict[str, Any] = {
        "started_at": _utc_now(),
        "steps_requested": steps,
        "steps": {},
    }
    errors: list[str] = state.setdefault("errors", [])

    for step in steps:
        if _SHUTDOWN:
            run_report["stopped_early"] = step
            break
        state["last_step"] = step
        _save_state(state)
        _LOGGER.info("Running step: %s", step) if _LOGGER else None

        if step == "vault":
            outcome = _step_vault(resume=resume, state=state)
        elif step == "digitalize":
            outcome = _step_digitalize(resume=resume, state=state)
        elif step == "supabase_sync":
            outcome = _step_supabase_sync()
        else:
            outcome = {"status": "skipped", "reason": f"unknown_step:{step}"}
            errors.append(f"unknown_step:{step}")

        run_report["steps"][step] = outcome
        if outcome.get("status") == "error":
            errors.append(f"{step}:{outcome.get('detail', 'error')}")

    run_report["finished_at"] = _utc_now()
    state["last_run_at"] = run_report["finished_at"]
    state["last_run"] = run_report
    state["runs_completed"] = int(state.get("runs_completed") or 0) + 1
    state["errors"] = errors[-50:]
    _save_state(state)
    return run_report


def _handle_signal(signum: int, _frame: Any) -> None:
    global _SHUTDOWN
    _SHUTDOWN = True
    name = signal.Signals(signum).name
    if _LOGGER:
        _LOGGER.info("Received %s — finishing current step then saving state", name)


def _stop_daemon() -> int:
    pid = _read_pid_file()
    if pid is None:
        print("No processor.pid file; processor not running?")
        return 1
    if not _pid_alive(pid):
        _remove_pid_file()
        print(f"Stale pid {pid}; removed pid file.")
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to pid {pid}")
    except ProcessLookupError:
        _remove_pid_file()
        print(f"Process {pid} already exited.")
        return 0
    return 0


def _daemon_loop(*, resume: bool, force: bool) -> int:
    global _LOGGER, _SHUTDOWN
    _LOGGER = _setup_logging()
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    _acquire_lock(force=force)
    state = _load_state()
    state.update(
        {
            "pid": os.getpid(),
            "started_at": state.get("started_at") or _utc_now(),
            "mode": "daemon",
            "interval_sec": _interval_sec(),
            "steps": _parse_steps(),
        }
    )
    _save_state(state)
    _LOGGER.info("Autonomous processor daemon started pid=%s", os.getpid())

    exit_code = 0
    try:
        while not _SHUTDOWN:
            try:
                _run_pipeline(resume=resume, state=state)
            except Exception:
                _LOGGER.exception("Pipeline run failed")
                exit_code = 1
            if _SHUTDOWN:
                break
            resume = True
            _LOGGER.info("Sleeping %s seconds until next cycle", _interval_sec())
            deadline = time.time() + _interval_sec()
            while time.time() < deadline and not _SHUTDOWN:
                time.sleep(min(5.0, deadline - time.time()))
    finally:
        state["pid"] = None
        state["stopped_at"] = _utc_now()
        state["mode"] = "stopped"
        _save_state(state)
        _remove_pid_file()
        _LOGGER.info("Autonomous processor daemon stopped")
    return exit_code


def _once_run(*, resume: bool, force: bool) -> int:
    global _LOGGER, _SHUTDOWN
    _LOGGER = _setup_logging()
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    _acquire_lock(force=force)
    state = _load_state()
    state.update({"pid": os.getpid(), "started_at": _utc_now(), "mode": "once", "steps": _parse_steps()})
    _save_state(state)
    try:
        report = _run_pipeline(resume=resume, state=state)
        print(json.dumps(report, indent=2))
        failed = [
            name
            for name, outcome in (report.get("steps") or {}).items()
            if (outcome or {}).get("status") == "error"
        ]
        return 1 if failed else 0
    finally:
        state["pid"] = None
        state["stopped_at"] = _utc_now()
        _save_state(state)
        _remove_pid_file()


def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomous vault/digitalize/supabase processor")
    parser.add_argument("--once", action="store_true", help="Single pipeline pass then exit")
    parser.add_argument("--daemon", action="store_true", help="Loop with PROCESSOR_INTERVAL_SEC sleep")
    parser.add_argument("--resume", action="store_true", help="Resume vault/digitalize checkpoints")
    parser.add_argument("--stop", action="store_true", help="SIGTERM process from processor.pid")
    parser.add_argument("--force", action="store_true", help="Replace running instance")
    args = parser.parse_args()

    if args.stop:
        return _stop_daemon()

    autonomous = os.getenv("PROCESSOR_AUTONOMOUS", "true").strip().lower()
    if autonomous in ("0", "false", "no", "off") and not args.force:
        print("PROCESSOR_AUTONOMOUS is disabled; set true or pass --force")
        return 0

    if args.daemon and args.once:
        parser.error("Use only one of --daemon or --once")
    if not args.daemon and not args.once:
        args.once = True

    if args.daemon:
        return _daemon_loop(resume=args.resume, force=args.force)
    return _once_run(resume=args.resume, force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
