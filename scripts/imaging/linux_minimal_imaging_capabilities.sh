#!/usr/bin/env bash
# Paste this ONE small script on Linux — creates imaging_capabilities.py only.
# Run: bash linux_minimal_imaging_capabilities.sh
set -euo pipefail
ROOT="${OMEIA_ROOT:-$HOME/data4TB/digital-notepad}"
mkdir -p "$ROOT/app_skeleton/api"
cat > "$ROOT/app_skeleton/api/imaging_capabilities.py" <<'PYEOF'
"""Runtime detection of optional imaging libraries."""
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
    checks = [
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
    tier_ready = {"core": True, "extended": True, "workstation": True, "desktop_gui": True}
    for label, module, attr, tier in checks:
        ok, detail = _try_import(module, attr)
        packages[label] = {"available": ok, "tier": tier, "detail": detail}
        if tier == "core" and not ok:
            tier_ready["core"] = False
    streaming_ready = packages["tifffile"]["available"] and packages["Pillow"]["available"]
    return {
        "streaming_ready": streaming_ready,
        "compression_codecs_ready": packages["imagecodecs"]["available"],
        "tier_ready": tier_ready,
        "packages": packages,
    }
PYEOF
echo "Created $ROOT/app_skeleton/api/imaging_capabilities.py"
cd "$ROOT"
source .venv/bin/activate
PYTHONPATH="$ROOT" python -c "from app_skeleton.api.imaging_capabilities import probe_imaging_stack; import json; print(json.dumps(probe_imaging_stack(), indent=2))"
