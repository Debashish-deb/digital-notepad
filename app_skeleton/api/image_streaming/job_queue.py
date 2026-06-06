"""Lightweight file-backed job queue for image inspection tasks."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app_skeleton.api.paths import BLUEPRINT_ROOT

LOGGER = logging.getLogger(__name__)

JOBS_PATH = BLUEPRINT_ROOT / "app_skeleton" / "data" / "image_streaming_jobs.json"

JOB_TYPES = frozenset({"inspect_image_metadata", "generate_image_thumbnail"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_jobs() -> dict[str, Any]:
    if not JOBS_PATH.is_file():
        return {"jobs": []}
    try:
        return json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        LOGGER.warning("job queue read failed: %s", exc)
        return {"jobs": []}


def _save_jobs(data: dict[str, Any]) -> None:
    JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    JOBS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


class ImageJobQueue:
    """In-memory view over a JSON job list."""

    def list_jobs(self, *, status: str | None = None) -> list[dict[str, Any]]:
        jobs = _load_jobs().get("jobs") or []
        if status:
            return [j for j in jobs if j.get("status") == status]
        return jobs

    def enqueue(self, job_type: str, asset_id: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if job_type not in JOB_TYPES:
            raise ValueError(f"Unknown job type: {job_type}")
        job = {
            "job_id": f"imgjob_{uuid.uuid4().hex[:12]}",
            "job_type": job_type,
            "asset_id": asset_id,
            "status": "pending",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "attempts": 0,
            "error": None,
            "payload": payload or {},
        }
        data = _load_jobs()
        jobs = data.get("jobs") or []
        jobs.append(job)
        data["jobs"] = jobs[-500:]
        _save_jobs(data)
        return job

    def enqueue_many(self, job_type: str, asset_ids: list[str]) -> list[dict[str, Any]]:
        return [self.enqueue(job_type, aid) for aid in asset_ids]

    def _update_job(self, job_id: str, **fields: Any) -> dict[str, Any] | None:
        data = _load_jobs()
        jobs = data.get("jobs") or []
        updated = None
        for job in jobs:
            if job.get("job_id") == job_id:
                job.update(fields)
                job["updated_at"] = _utc_now()
                updated = job
                break
        if updated:
            _save_jobs(data)
        return updated

    def mark_running(self, job_id: str) -> None:
        data = _load_jobs()
        for job in data.get("jobs") or []:
            if job.get("job_id") == job_id:
                job["status"] = "running"
                job["attempts"] = int(job.get("attempts") or 0) + 1
                job["updated_at"] = _utc_now()
                _save_jobs(data)
                return

    def mark_done(self, job_id: str) -> None:
        self._update_job(job_id, status="done", error=None)

    def mark_failed(self, job_id: str, error: str) -> None:
        self._update_job(job_id, status="failed", error=error)

    def retry_failed(self) -> int:
        data = _load_jobs()
        count = 0
        for job in data.get("jobs") or []:
            if job.get("status") == "failed":
                job["status"] = "pending"
                job["error"] = None
                job["updated_at"] = _utc_now()
                count += 1
        if count:
            _save_jobs(data)
        return count

    def process_pending(
        self,
        handlers: dict[str, Callable[[dict[str, Any]], None]],
        *,
        limit: int = 10,
    ) -> dict[str, int]:
        """Process up to `limit` pending jobs synchronously."""
        data = _load_jobs()
        jobs = data.get("jobs") or []
        done = failed = 0
        processed = 0
        for job in jobs:
            if processed >= limit:
                break
            if job.get("status") != "pending":
                continue
            handler = handlers.get(job.get("job_type") or "")
            if not handler:
                continue
            job["status"] = "running"
            job["attempts"] = int(job.get("attempts") or 0) + 1
            job["updated_at"] = _utc_now()
            _save_jobs(data)
            try:
                handler(job)
                job["status"] = "done"
                job["error"] = None
                done += 1
            except Exception as exc:
                job["status"] = "failed"
                job["error"] = str(exc)
                failed += 1
            job["updated_at"] = _utc_now()
            _save_jobs(data)
            processed += 1
        return {"processed": processed, "done": done, "failed": failed}
