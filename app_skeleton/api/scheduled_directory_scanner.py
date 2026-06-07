"""Daily background scan of configured watch directories into the document inventory."""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app_skeleton.api.data_layout import inventory_json, inventory_write_dir

LOGGER = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_CONFIG_PATH = _REPO_ROOT / "configs" / "scheduled_scan_directories.json"
_DEFAULT_INTERVAL_HOURS = 24


class ScheduledDirectoryScanner:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_run: dict[str, Any] | None = None
        self._running = False

    def load_config(self) -> dict[str, Any]:
        if not _CONFIG_PATH.is_file():
            return {"enabled": False, "directories": []}
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"enabled": False, "directories": []}
        except (json.JSONDecodeError, OSError) as exc:
            LOGGER.warning("Failed to read scheduled scan config: %s", exc)
            return {"enabled": False, "directories": []}

    def _resolve_path(self, raw: str) -> Path | None:
        text = (raw or "").strip()
        if not text:
            return None
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = (_REPO_ROOT / path).resolve()
        return path

    def run_scan(self, *, reason: str = "manual") -> dict[str, Any]:
        from scripts.digitalization.build_raw_asset_inventory import (
            _load_prior_inventory,
            scan_root_tree,
        )
        from app_skeleton.api.document_library_service import invalidate_cache

        started = datetime.now(timezone.utc).isoformat()
        config = self.load_config()
        output_dir = inventory_write_dir()
        prior_by_path = _load_prior_inventory(output_dir)
        directories = config.get("directories") or []

        refreshed_ids: set[str] = set()
        dir_results: list[dict[str, Any]] = []
        new_rows_by_path: dict[str, dict[str, Any]] = {}

        for entry in directories:
            if not isinstance(entry, dict) or not entry.get("enabled", True):
                continue
            watch_id = str(entry.get("id") or "").strip()
            if not watch_id:
                continue
            root = self._resolve_path(str(entry.get("path") or ""))
            if root is None:
                dir_results.append({
                    "id": watch_id,
                    "label": entry.get("label"),
                    "status": "skipped",
                    "reason": "path_not_configured",
                })
                continue
            if not root.is_dir():
                dir_results.append({
                    "id": watch_id,
                    "label": entry.get("label"),
                    "path": str(root),
                    "status": "skipped",
                    "reason": "directory_missing",
                })
                continue

            refreshed_ids.add(watch_id)
            scanned = scan_root_tree(
                root,
                logical_prefix=f"watch/{watch_id}",
                storage_provider=f"scheduled_watch:{watch_id}",
                prior_rows=prior_by_path,
                watch_source_id=watch_id,
                watch_label=str(entry.get("label") or watch_id),
            )
            for row in scanned:
                lp = (row.get("logical_path") or "").strip()
                if lp:
                    new_rows_by_path[lp] = row
            dir_results.append({
                "id": watch_id,
                "label": entry.get("label"),
                "path": str(root),
                "status": "ok",
                "files_found": len(scanned),
            })

        merged: dict[str, dict[str, Any]] = {
            lp: row
            for lp, row in prior_by_path.items()
            if str(row.get("watch_source_id") or "") not in refreshed_ids
        }
        merged.update(new_rows_by_path)
        rows = sorted(merged.values(), key=lambda r: (r.get("logical_path") or "").lower())

        json_path = inventory_json()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        invalidate_cache()

        finished = datetime.now(timezone.utc).isoformat()
        report = {
            "status": "ok",
            "reason": reason,
            "started_at": started,
            "finished_at": finished,
            "directories": dir_results,
            "refreshed_watch_ids": sorted(refreshed_ids),
            "inventory_rows": len(rows),
            "watch_rows_added": len(new_rows_by_path),
        }

        if os.getenv("SCHEDULED_SCAN_SYNC_POSTGRES", "false").lower() in ("1", "true", "yes"):
            try:
                from app_skeleton.api.raw_vault_store import sync_inventory_to_postgres
                report["postgres_sync"] = sync_inventory_to_postgres()
            except Exception as exc:
                LOGGER.exception("Postgres sync after scheduled scan failed")
                report["postgres_sync"] = {"status": "error", "detail": str(exc)}

        with self._lock:
            self._last_run = report
        LOGGER.info(
            "Scheduled directory scan complete (%s): %s watch dirs, %s inventory rows",
            reason,
            len(refreshed_ids),
            len(rows),
        )
        return report

    def _scan_loop(self) -> None:
        config = self.load_config()
        schedule = config.get("schedule") or {}
        interval_hours = float(schedule.get("interval_hours") or _DEFAULT_INTERVAL_HOURS)
        interval_sec = max(3600.0, interval_hours * 3600.0)
        startup_delay = float(schedule.get("startup_delay_seconds") or 90)

        if schedule.get("run_at_startup", True):
            self._stop.wait(startup_delay)
            if not self._stop.is_set():
                self._run_guarded("startup")

        while not self._stop.is_set():
            self._stop.wait(interval_sec)
            if self._stop.is_set():
                break
            self._run_guarded("scheduled")

    def _run_guarded(self, reason: str) -> None:
        if self._running:
            LOGGER.info("Scheduled scan skipped (%s): previous run still active", reason)
            return
        self._running = True
        try:
            self.run_scan(reason=reason)
        except Exception:
            LOGGER.exception("Scheduled directory scan failed (%s)", reason)
            with self._lock:
                self._last_run = {
                    "status": "error",
                    "reason": reason,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                }
        finally:
            self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def status(self) -> dict[str, Any]:
        config = self.load_config()
        with self._lock:
            last_run = dict(self._last_run) if self._last_run else None
        return {
            "enabled": bool(config.get("enabled", True)),
            "config_path": str(_CONFIG_PATH),
            "interval_hours": (config.get("schedule") or {}).get("interval_hours", _DEFAULT_INTERVAL_HOURS),
            "directories": config.get("directories") or [],
            "running": self._running,
            "last_run": last_run,
        }

    def start(self) -> None:
        config = self.load_config()
        if not config.get("enabled", True):
            LOGGER.info("Scheduled directory scanner disabled in config")
            return
        if self._thread:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._scan_loop,
            name="scheduled-directory-scanner",
            daemon=True,
        )
        self._thread.start()
        LOGGER.info("Scheduled directory scanner started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None


scheduled_directory_scanner = ScheduledDirectoryScanner()
