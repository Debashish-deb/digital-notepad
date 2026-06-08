"""Probe optional workers and imaging/LLM capabilities (no heavy imports at load)."""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Any


def _env_bool(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in ("1", "true", "yes", "on")


def probe_database_root() -> dict[str, Any]:
    root = (os.getenv("DATABASE_ROOT") or "").strip()
    path = Path(root) if root else None
    ok = bool(path and path.is_dir())
    return {
        "configured": bool(root),
        "path_set": bool(root),
        "readable": ok,
        "exists": ok,
    }


def probe_projects_root() -> dict[str, Any]:
    root = (os.getenv("PROJECTS_ROOT") or os.getenv("DATABASE_ROOT") or "").strip()
    path = Path(root) if root else None
    ok = bool(path and path.is_dir())
    return {
        "configured": bool(root),
        "readable": ok,
    }


def probe_ollama() -> dict[str, Any]:
    base = (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
    reachable = False
    detail = None
    if _env_bool("OMEIA_SKIP_OLLAMA_PROBE", "false"):
        return {"base_url": base, "reachable": None, "skipped": True}
    try:
        import requests

        r = requests.get(f"{base}/api/tags", timeout=2.5)
        reachable = r.status_code == 200
        if not reachable:
            detail = f"HTTP {r.status_code}"
    except Exception as exc:
        detail = str(exc)[:160]
    return {"base_url": base, "reachable": reachable, "detail": detail}


def probe_qdrant() -> dict[str, Any]:
    url = (os.getenv("QDRANT_URL") or "").strip()
    if not url:
        return {"configured": False, "reachable": False}
    reachable = False
    detail = None
    try:
        import requests

        r = requests.get(f"{url.rstrip('/')}/collections", timeout=2.5)
        reachable = r.status_code == 200
        if not reachable:
            detail = f"HTTP {r.status_code}"
    except Exception as exc:
        detail = str(exc)[:160]
    return {"configured": True, "url": url, "reachable": reachable, "detail": detail}


def probe_docker_worker() -> dict[str, Any]:
    compose = Path("docker-compose.imaging.yml")
    script = Path("infra/scripts/docker/build_imaging_worker.sh")
    return {
        "imaging_compose_present": compose.is_file(),
        "build_script_present": script.is_file(),
        "docker_cli": shutil.which("docker") is not None,
        "remote_gpu_flag": _env_bool("OMEIA_REMOTE_GPU_WORKER_ENABLED", "false"),
    }


def probe_host_signals() -> dict[str, Any]:
    system = platform.system().lower()
    is_linux = system == "linux"
    database_ok = probe_database_root().get("readable")
    return {
        "os": system,
        "machine": platform.machine(),
        "is_linux": is_linux,
        "linux_workstation_signals": is_linux and database_ok,
        "cpu_count": os.cpu_count(),
    }


def probe_all_capabilities() -> dict[str, Any]:
    imaging: dict[str, Any] = {"streaming_ready": False, "packages": {}}
    try:
        from omeia.api.imaging_capabilities import probe_imaging_stack

        imaging = probe_imaging_stack()
    except Exception as exc:
        imaging["error"] = str(exc)[:200]

    return {
        "host": probe_host_signals(),
        "database_root": probe_database_root(),
        "projects_root": probe_projects_root(),
        "ollama": probe_ollama(),
        "qdrant": probe_qdrant(),
        "imaging": imaging,
        "gpu": imaging.get("gpu") or {},
        "docker_worker": probe_docker_worker(),
        "flags": {
            "ocr_enabled": _env_bool("ENABLE_OCR", "false"),
            "vectorization_enabled": _env_bool("VECTORIZATION_ENABLED", "false"),
            "knowledge_indexer_enabled": _env_bool("KNOWLEDGE_INDEXER_ENABLED", "false"),
        },
    }
