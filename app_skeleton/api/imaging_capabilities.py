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

    return {
        "streaming_ready": streaming_ready,
        "compression_codecs_ready": compression_ready,
        "tier_ready": tier_ready,
        "packages": packages,
        "recommendations": _recommendations(packages, streaming_ready, compression_ready),
    }


def _recommendations(
    packages: dict[str, dict[str, Any]],
    streaming_ready: bool,
    compression_ready: bool,
) -> list[str]:
    recs: list[str] = []
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
    return recs
