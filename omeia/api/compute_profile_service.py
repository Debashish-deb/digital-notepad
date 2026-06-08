"""Adaptive compute profiles — select safe runtime tier without fake GPU."""
from __future__ import annotations

import os
from typing import Any

from omeia.api.platform_flags import adaptive_compute_enabled, low_resource_mode_enabled
from omeia.api.worker_capability_probe import probe_all_capabilities

PROFILES = (
    "LOW_END_LAPTOP",
    "MEDIUM_LAPTOP",
    "LINUX_WORKSTATION",
    "REMOTE_GPU_WORKER",
    "CLOUD_TEACHER",
)

IMAGE_MODES = (
    "thumbnail_only",
    "metadata_only",
    "tile_streaming",
    "high_performance",
    "analysis_overlay",
)


def _env_bool(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in ("1", "true", "yes", "on")


def detect_compute_profile(capabilities: dict[str, Any] | None = None) -> str:
    """Return active compute profile id."""
    override = (os.getenv("OMEIA_COMPUTE_HOST_PROFILE") or "").strip().upper()
    if override in PROFILES:
        return override

    if low_resource_mode_enabled():
        return "LOW_END_LAPTOP"

    caps = capabilities or probe_all_capabilities()
    host = caps.get("host") or {}
    imaging = caps.get("imaging") or {}
    gpu = caps.get("gpu") or {}
    ollama = caps.get("ollama") or {}

    if _env_bool("OMEIA_REMOTE_GPU_WORKER_ENABLED", "false") and (
        gpu.get("cuda_available") or gpu.get("nvidia_smi")
    ):
        return "REMOTE_GPU_WORKER"

    if host.get("linux_workstation_signals") and ollama.get("reachable"):
        return "LINUX_WORKSTATION"

    if imaging.get("streaming_ready") and ollama.get("reachable"):
        return "MEDIUM_LAPTOP"

    if host.get("is_linux") and caps.get("database_root", {}).get("readable"):
        return "LINUX_WORKSTATION"

    return "LOW_END_LAPTOP"


def image_viewer_mode_for_profile(profile: str, capabilities: dict[str, Any]) -> str:
    imaging = capabilities.get("imaging") or {}
    streaming = bool(imaging.get("streaming_ready"))
    if not streaming:
        return "metadata_only"
    if profile in ("LOW_END_LAPTOP",):
        return "thumbnail_only" if not _env_bool("IMAGE_FORCE_TILE_STREAMING", "false") else "tile_streaming"
    packages = imaging.get("packages") or {}
    pyvips = packages.get("pyvips") or {}
    if profile in ("LINUX_WORKSTATION", "REMOTE_GPU_WORKER") and pyvips.get("available"):
        return "high_performance"
    return "tile_streaming" if streaming else "thumbnail_only"


def model_tier_for_profile(profile: str) -> str:
    return {
        "LOW_END_LAPTOP": "small",
        "MEDIUM_LAPTOP": "medium",
        "LINUX_WORKSTATION": "large",
        "REMOTE_GPU_WORKER": "xlarge",
        "CLOUD_TEACHER": "teacher",
    }.get(profile, "small")


def heavy_job_policy(profile: str) -> dict[str, Any]:
    queue_required = _env_bool("OMEIA_HEAVY_JOBS_REQUIRE_QUEUE", "true")
    cloud_ok = _env_bool("OMEIA_CLOUD_TEACHER_ENABLED", "false") and profile == "CLOUD_TEACHER"
    return {
        "segmentation": profile in ("LINUX_WORKSTATION", "REMOTE_GPU_WORKER"),
        "ocr": profile in ("LINUX_WORKSTATION", "MEDIUM_LAPTOP", "REMOTE_GPU_WORKER"),
        "strategy_report": profile in ("LINUX_WORKSTATION", "REMOTE_GPU_WORKER", "MEDIUM_LAPTOP"),
        "cloud_allowed": cloud_ok,
        "queue_if_unavailable": queue_required,
        "sensitive_data_never_cloud": True,
    }


def build_compute_status() -> dict[str, Any]:
    if not adaptive_compute_enabled():
        return {
            "adaptive_compute_enabled": False,
            "profile": "LEGACY_FIXED",
            "message": "Set OMEIA_ADAPTIVE_COMPUTE=true to enable profile routing.",
        }

    caps = probe_all_capabilities()
    profile = detect_compute_profile(caps)
    return {
        "adaptive_compute_enabled": True,
        "profile": profile,
        "model_tier": model_tier_for_profile(profile),
        "image_viewer_mode": image_viewer_mode_for_profile(profile, caps),
        "heavy_jobs": heavy_job_policy(profile),
        "auto_model_downgrade": _env_bool("OMEIA_AUTO_MODEL_DOWNGRADE", "true"),
        "low_resource_mode": low_resource_mode_enabled(),
        "capabilities": caps,
        "references": {
            "adaptive_compute_doc": "/docs/ADAPTIVE_COMPUTE_PROFILES.md",
            "image_viewer_doc": "/docs/SCIENTIFIC_IMAGE_VIEWER_REFERENCES.md",
        },
    }
