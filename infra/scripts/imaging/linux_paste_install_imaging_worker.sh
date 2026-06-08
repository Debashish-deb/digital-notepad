#!/usr/bin/env bash
# Paste this ENTIRE file on Linux, save, run: bash linux_paste_install_imaging_worker.sh
# Creates imaging-worker Docker setup under ~/data4TB/digital-notepad — no scp needed.
set -euo pipefail

ROOT="${OMEIA_ROOT:-$HOME/data4TB/digital-notepad}"
cd "$ROOT"

echo "Installing imaging-worker files under $ROOT"

mkdir -p docker/imaging-worker omeia/api scripts

cat > docker-compose.imaging.yml <<'EOF'
networks:
  omeia-imaging:
    driver: bridge

services:
  imaging-worker:
    build:
      context: .
      dockerfile: docker/imaging-worker/Dockerfile
      args:
        IMAGING_INCLUDE_NAPARI: ${IMAGING_INCLUDE_NAPARI:-1}
    image: omeia-imaging-worker:latest
    container_name: omeia-imaging-worker
    networks: [omeia-imaging]
    volumes:
      - ${DATABASE_ROOT:-../OMEIA-database}:/data/database:ro
    environment:
      DATABASE_ROOT: /data/database
    restart: "no"
    security_opt:
      - no-new-privileges:true
EOF

cat > docker/imaging-worker/environment-core.yml <<'EOF'
name: omeia-imaging
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pip
  - tifffile
  - imagecodecs
  - numpy
  - pillow
  - zarr
  - fsspec
  - dask
  - scikit-image
  - pyvips
  - openslide-python
  - aicsimageio
  - napari
  - pyqt
  - pip:
    - deeptile>=2.0
    - fastapi
    - uvicorn
    - httpx
EOF

cat > docker/imaging-worker/environment-cycif-amd64.yml <<'EOF'
name: omeia-imaging
channels:
  - conda-forge
dependencies:
  - bioformats2raw
  - raw2ometiff
  - ashlar
EOF

cat > docker/imaging-worker/Dockerfile <<'EOF'
FROM condaforge/mambaforge:latest
ARG IMAGING_INCLUDE_NAPARI=1
ARG TARGETARCH
ENV PYTHONUNBUFFERED=1
ENV MAMBA_NO_LOW_SPEED_LIMIT=1
WORKDIR /opt/omeia
COPY docker/imaging-worker/environment-core.yml /tmp/environment-core.yml
COPY docker/imaging-worker/environment-cycif-amd64.yml /tmp/environment-cycif-amd64.yml
RUN if [ "$IMAGING_INCLUDE_NAPARI" = "0" ]; then \
      grep -v -E '^\s*-\s*(napari|pyqt)\s*$' /tmp/environment-core.yml > /tmp/environment.slim.yml; \
    else cp /tmp/environment-core.yml /tmp/environment.slim.yml; fi \
 && mamba env create -f /tmp/environment.slim.yml && mamba clean -afy
RUN if [ "$TARGETARCH" = "amd64" ]; then \
      mamba env update -n omeia-imaging -f /tmp/environment-cycif-amd64.yml && mamba clean -afy; \
    else echo "Skipping CycIF packages on ${TARGETARCH}"; fi
ENV PATH=/opt/conda/envs/omeia-imaging/bin:$PATH
COPY omeia/api/imaging_capabilities.py /opt/omeia/imaging_capabilities.py
COPY docker/imaging-worker/healthcheck.py /opt/omeia/healthcheck.py
CMD ["python", "/opt/omeia/healthcheck.py"]
EOF

cat > omeia/api/imaging_capabilities.py <<'PYEOF'
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

cat > docker/imaging-worker/healthcheck.py <<'PYEOF'
#!/usr/bin/env python3
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from imaging_capabilities import probe_imaging_stack
if __name__ == "__main__":
    report = probe_imaging_stack()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report.get("streaming_ready") else 1)
PYEOF

cat > scripts/docker/build_imaging_worker.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
docker compose -f docker-compose.imaging.yml build imaging-worker
docker compose -f docker-compose.imaging.yml run --rm imaging-worker
EOF
chmod +x scripts/docker/build_imaging_worker.sh

echo "Files created:"
ls -la docker-compose.imaging.yml docker/imaging-worker/ scripts/docker/build_imaging_worker.sh

echo ""
echo "=== Building (takes 5-15 min first time) ==="
export DATABASE_ROOT="${DATABASE_ROOT:-$HOME/data4TB/OMEIA-database}"
docker compose -f docker-compose.imaging.yml build imaging-worker
docker compose -f docker-compose.imaging.yml run --rm imaging-worker

echo "DONE."
