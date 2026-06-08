"""Runtime detection of optional imaging libraries — no imports at module load."""
from __future__ import annotations

from typing import Any


def _try_import(module: str, attr: str | None = None) -> tuple[bool, str | None]:
    try:
        mod = __import__(module, fromlist=[attr] if attr else [])
        if attr:
            getattr(mod, attr)
        version = getattr(mod, "__version__", None)
        return True, str(version) if version else None
    except Exception as exc:
        return False, str(exc)[:120]


def _probe_gpu() -> dict[str, Any]:
    """Best-effort CUDA / GPU detection (optional for TIFF streaming)."""
    info: dict[str, Any] = {
        "nvidia_smi": False,
        "cuda_available": False,
        "device_name": None,
        "detail": None,
    }
    import shutil
    import subprocess

    if shutil.which("nvidia-smi"):
        info["nvidia_smi"] = True
        try:
            out = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,memory.total",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if out.returncode == 0 and out.stdout.strip():
                info["device_name"] = out.stdout.strip().splitlines()[0]
        except Exception as exc:
            info["detail"] = str(exc)[:120]

    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            info["cuda_available"] = True
            if not info["device_name"]:
                info["device_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        if not info["detail"]:
            info["detail"] = "torch not installed"
    except Exception as exc:
        info["detail"] = str(exc)[:120]

    return info


def probe_imaging_stack() -> dict[str, Any]:
    """Report which imaging packages are available on this host."""
    checks: list[tuple[str, str, str | None, str]] = [
        # name, import target, attr, tier
        ("tifffile", "tifffile", None, "core"),
        ("imagecodecs", "imagecodecs", None, "core"),
        ("numpy", "numpy", None, "core"),
        ("Pillow", "PIL", None, "core"),
        ("zarr", "zarr", None, "extended"),
        ("fsspec", "fsspec", None, "extended"),
        ("dask", "dask", None, "extended"),
        ("scikit-image", "skimage", None, "extended"),
        ("pyvips", "pyvips", None, "workstation"),
        ("openslide", "openslide", None, "workstation"),
        ("aicsimageio", "aicsimageio", None, "workstation"),
        ("deeptile", "deeptile", None, "workstation"),
        ("napari", "napari", None, "desktop_gui"),
        ("bioformats", "bioformats", None, "workstation_jvm"),
    ]

    packages: dict[str, dict[str, Any]] = {}
    tier_ready: dict[str, bool] = {"core": True, "extended": True, "workstation": True, "desktop_gui": True}

    for label, module, attr, tier in checks:
        ok, detail = _try_import(module, attr)
        packages[label] = {
            "available": ok,
            "tier": tier,
            "detail": detail if ok else detail,
        }
        if tier == "core" and not ok:
            tier_ready["core"] = False

    streaming_ready = packages["tifffile"]["available"] and packages["Pillow"]["available"]
    compression_ready = packages["imagecodecs"]["available"]

    gpu = _probe_gpu()

    return {
        "streaming_ready": streaming_ready,
        "compression_codecs_ready": compression_ready,
        "tier_ready": tier_ready,
        "packages": packages,
        "gpu": gpu,
        "recommendations": _recommendations(packages, streaming_ready, compression_ready, gpu),
    }


def _recommendations(
    packages: dict[str, dict[str, Any]],
    streaming_ready: bool,
    compression_ready: bool,
    gpu: dict[str, Any] | None = None,
) -> list[str]:
    recs: list[str] = []
    gpu = gpu or {}
    if not packages["tifffile"]["available"]:
        recs.append("Install tifffile: pip install tifffile (required for TIFF metadata/tiles)")
    if not packages["imagecodecs"]["available"]:
        recs.append("Install imagecodecs: pip install imagecodecs (JPEG/LZW/deflate TIFF pages)")
    if streaming_ready and not compression_ready:
        recs.append("Some compressed TIFFs may fail tiles until imagecodecs is installed")
    if not packages["pyvips"]["available"]:
        recs.append("For faster region reads on Linux, add pyvips to Docker/workstation image")
    if not packages["openslide"]["available"]:
        recs.append("Whole-slide formats (.svs, .ndpi) need openslide on Linux workstation Docker")
    if not packages["zarr"]["available"]:
        recs.append("OME-Zarr support later: pip install zarr fsspec (or use Docker imaging stack)")
    if packages["napari"]["available"]:
        recs.append("napari is installed — desktop GUI only; not used by streaming API")
    elif not packages["napari"]["available"]:
        recs.append("napari belongs on analyst workstations/Docker desktop env, not API server")
    if not gpu.get("nvidia_smi") and not gpu.get("cuda_available"):
        recs.append(
            "GPU not detected — StarDist/Mesmer segmentation runs on CPU or external HPC; "
            "install NVIDIA drivers on Linux workstation for local GPU pipelines"
        )
    return recs
