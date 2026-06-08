"""Choose runtime for heavy tasks — local, Linux worker, queue, or blocked."""
from __future__ import annotations

from typing import Any

from omeia.api.compute_profile_service import build_compute_status, detect_compute_profile
from omeia.api.platform_flags import adaptive_compute_enabled
from omeia.api.worker_capability_probe import probe_all_capabilities

TASK_RUNTIMES = ("local", "linux_workstation", "docker_worker", "queue", "blocked", "cloud")


def select_runtime(
    task: str,
    *,
    sensitive: bool = False,
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    task examples: greeting, chat, ocr, vectorize, image_tile, image_segment, strategy_report
    """
    if not adaptive_compute_enabled():
        return {
            "task": task,
            "runtime": "local",
            "reason": "OMEIA_ADAPTIVE_COMPUTE=false — legacy fixed routing",
            "degraded": False,
        }

    caps = capabilities or probe_all_capabilities()
    profile = detect_compute_profile(caps)
    heavy = (build_compute_status().get("heavy_jobs") or {}) if adaptive_compute_enabled() else {}

    if task in ("greeting", "smalltalk", "navigation"):
        return {"task": task, "runtime": "local", "profile": profile, "reason": "fast path", "degraded": False}

    if task in ("ocr", "vectorize", "ingestion"):
        if profile in ("LINUX_WORKSTATION", "REMOTE_GPU_WORKER"):
            return {"task": task, "runtime": "linux_workstation", "profile": profile, "reason": "server CPU worker", "degraded": False}
        if heavy.get("queue_if_unavailable"):
            return {"task": task, "runtime": "queue", "profile": profile, "reason": "queue on thin client", "degraded": True}
        return {"task": task, "runtime": "blocked", "profile": profile, "reason": "no safe OCR/vector runtime", "degraded": True}

    if task in ("image_segment", "mesmer", "stardist", "deepcell"):
        if profile == "REMOTE_GPU_WORKER":
            return {"task": task, "runtime": "docker_worker", "profile": profile, "reason": "GPU worker", "degraded": False}
        if profile == "LINUX_WORKSTATION" and caps.get("docker_worker", {}).get("docker_cli"):
            return {"task": task, "runtime": "docker_worker", "profile": profile, "reason": "imaging-worker container", "degraded": False}
        if heavy.get("queue_if_unavailable"):
            return {"task": task, "runtime": "queue", "profile": profile, "reason": "segmentation requires worker queue", "degraded": True}
        return {"task": task, "runtime": "blocked", "profile": profile, "reason": "segmentation not on laptop", "degraded": True}

    if task in ("strategy_report", "research_strategy", "expert_chat"):
        if sensitive and heavy.get("sensitive_data_never_cloud"):
            if profile in ("LINUX_WORKSTATION", "REMOTE_GPU_WORKER", "MEDIUM_LAPTOP"):
                return {"task": task, "runtime": "linux_workstation", "profile": profile, "reason": "local Ollama + retrieval", "degraded": False}
            return {"task": task, "runtime": "queue", "profile": profile, "reason": "sensitive — wait for workstation", "degraded": True}
        if not sensitive and heavy.get("cloud_allowed"):
            return {"task": task, "runtime": "cloud", "profile": profile, "reason": "cloud teacher optional", "degraded": False}
        if profile in ("LINUX_WORKSTATION", "REMOTE_GPU_WORKER", "MEDIUM_LAPTOP"):
            return {"task": task, "runtime": "linux_workstation", "profile": profile, "reason": "Ollama expert path", "degraded": False}
        return {"task": task, "runtime": "local", "profile": profile, "reason": "downgraded local model", "degraded": True}

    if task in ("image_tile", "image_thumbnail", "image_manifest"):
        streaming = bool((caps.get("imaging") or {}).get("streaming_ready"))
        if streaming:
            return {"task": task, "runtime": "linux_workstation", "profile": profile, "reason": "streaming API", "degraded": False}
        return {"task": task, "runtime": "local", "profile": profile, "reason": "metadata/thumbnail only", "degraded": True}

    return {"task": task, "runtime": "local", "profile": profile, "reason": "default local", "degraded": False}
