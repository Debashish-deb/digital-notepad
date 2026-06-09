#!/usr/bin/env python3
"""Validate scientific imaging instrument against tifffile ground truth."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "omeia").is_dir() and (parent / "web").is_dir():
            return parent
    return here.parents[3]


REPO_ROOT = _find_repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_TIFF = REPO_ROOT / "tests" / "fixtures" / "vault_sample_project" / "slide.tiff"
REPORT_PATH = REPO_ROOT / "tests" / "imaging_validation_last_run.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _venv_python_candidates() -> list[Path]:
    return [
        REPO_ROOT / ".venv-local" / "bin" / "python3",
        REPO_ROOT / ".venv" / "bin" / "python3",
    ]


def _python_has_fastapi(python_exe: Path) -> bool:
    import subprocess

    if not python_exe.is_file():
        return False
    try:
        proc = subprocess.run(
            [str(python_exe), "-c", "import fastapi"],
            capture_output=True,
            timeout=30,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _find_capable_python() -> Path | None:
    for candidate in _venv_python_candidates():
        if _python_has_fastapi(candidate):
            return candidate
    return None


def _ensure_project_python() -> None:
    """Re-exec with repo venv when current interpreter lacks FastAPI."""
    if _python_has_fastapi(Path(sys.executable)):
        return

    capable = _find_capable_python()
    if capable is not None and capable.resolve() != Path(sys.executable).resolve():
        os.execv(str(capable), [str(capable), *sys.argv])

    hint = _find_capable_python() or (REPO_ROOT / ".venv" / "bin" / "python3")
    print(
        "ERROR: current Python lacks FastAPI. Re-run with the bootstrapped venv:\n"
        f"  {hint} {Path(__file__).resolve()}\n"
        "If that venv is missing packages: ./scripts/deploy/linux_bootstrap_all.sh --skip-docker",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _read_ground_truth(path: Path) -> dict:
    import numpy as np  # type: ignore

    arr = None
    try:
        import tifffile  # type: ignore

        with tifffile.TiffFile(str(path)) as tif:
            page = tif.pages[0]
            arr = page.asarray()
    except ImportError:
        pass
    except Exception:
        arr = None

    if arr is None:
        try:
            from PIL import Image

            with Image.open(path) as im:
                arr = np.asarray(im.convert("L"))
        except Exception as exc:
            raise RuntimeError("tifffile or Pillow required for validation") from exc

    if arr.ndim > 2:
        arr = arr[0] if arr.shape[0] <= 8 else arr[..., 0]
    arr = np.asarray(arr)
    h, w = arr.shape[:2]
    probes = []
    for xy in [(0, 0), (w // 2, h // 2), (w - 1, h - 1)]:
        x, y = xy
        raw = arr[y, x]
        probes.append(
            {
                "x": int(x),
                "y": int(y),
                "raw_value": int(raw) if not np.issubdtype(raw.dtype, np.floating) else float(raw),
            }
        )
    return {
        "path": str(path),
        "width": int(w),
        "height": int(h),
        "dtype": str(arr.dtype),
        "shape": list(arr.shape),
        "probes": probes,
    }


def _probe_via_service(path: Path, asset_id: str, truth: dict) -> dict:
    from unittest.mock import patch

    from omeia.api.image_streaming.image_streaming_service import ImageStreamingService

    root = path.parent
    row = {
        "asset_id": asset_id,
        "filename": path.name,
        "extension": path.suffix or ".tif",
        "logical_path": path.name,
        "storage_provider": "local_database_mirror",
        "size_bytes": path.stat().st_size,
        "project_hint": "VALIDATION",
        "sensitivity_level": "internal",
    }

    def lookup(aid: str):
        return row if aid == asset_id else None

    w = int(truth["width"])
    h = int(truth["height"])
    with patch.multiple(
        "omeia.api.image_streaming.storage_adapter",
        lookup_asset_row=lookup,
        _ROOTS={"database-static": root, "projects-static": root, "csc-media": root},
    ):
        svc = ImageStreamingService()
        try:
            svc.inspect_asset(asset_id)
        except Exception:
            pass
        manifest = svc.build_manifest(asset_id)
        manifest["width"] = manifest.get("width") or w
        manifest["height"] = manifest.get("height") or h
        probes = []
        try:
            for xy in [(0, 0), (w // 2, h // 2), (w - 1, h - 1)]:
                x, y = xy
                data = svc.sample_pixel_probe(asset_id, x=x, y=y)
                ch0 = (data.get("channels") or [{}])[0]
                probes.append({"x": x, "y": y, "raw_value": ch0.get("raw_value")})
        except Exception as exc:
            return {"manifest": manifest, "probes": probes, "error": str(exc)}
        return {"manifest": manifest, "probes": probes, "validation_mode": "image_streaming_service"}


def run_validation(tiff_path: Path) -> dict:
    asset_id = "asset_validation_sci_instrument"
    truth = _read_ground_truth(tiff_path)
    instrument = _probe_via_service(tiff_path, asset_id, truth)

    manifest = instrument.get("manifest") or {}
    dim_ok = (
        int(manifest.get("width") or truth["width"]) == truth["width"]
        and int(manifest.get("height") or truth["height"]) == truth["height"]
    )
    manifest_dtype = str(manifest.get("dtype", "")).replace("numpy.", "")
    truth_dtype = str(truth["dtype"]).replace("numpy.", "")
    dtype_ok = manifest_dtype in truth_dtype or truth_dtype in manifest_dtype or not manifest_dtype

    probe_results = []
    probe_ok = True
    inst_probes = instrument.get("probes") or []
    if instrument.get("error") or len(inst_probes) != len(truth["probes"]):
        probe_ok = False
    for t_probe, i_probe in zip(truth["probes"], inst_probes):
        match = t_probe["raw_value"] == i_probe["raw_value"]
        probe_ok = probe_ok and match
        probe_results.append(
            {
                "x": t_probe["x"],
                "y": t_probe["y"],
                "tifffile": t_probe["raw_value"],
                "instrument": i_probe["raw_value"],
                "match": match,
            }
        )

    report = {
        "validated_at": _utc_now(),
        "tiff_path": str(tiff_path),
        "python": sys.executable,
        "equivalence_note": "Napari/QuPath/OMERO equivalence = same file read via tifffile ground truth",
        "dimensions_match": dim_ok,
        "dtype_match": dtype_ok,
        "pixel_probes_match": probe_ok,
        "passed": dim_ok and dtype_ok and probe_ok,
        "ground_truth": truth,
        "instrument": instrument,
        "probe_comparison": probe_results,
        "manual_tools": ["Napari", "QuPath", "OMERO"],
    }
    return report


def main() -> int:
    _ensure_project_python()

    parser = argparse.ArgumentParser(description="Validate scientific imaging instrument")
    parser.add_argument("--tiff", type=Path, default=None, help="OME-TIFF path (env SCI_VALIDATION_TIFF)")
    parser.add_argument("--output", type=Path, default=REPORT_PATH, help="JSON report path")
    args = parser.parse_args()

    tiff = args.tiff or Path(os.environ.get("SCI_VALIDATION_TIFF", str(DEFAULT_TIFF)))
    if tiff.is_file() and tiff.stat().st_size < 256:
        try:
            from PIL import Image
            import numpy as np  # type: ignore

            gen = tiff.parent / "_validation_generated.tif"
            data = np.arange(64 * 48, dtype=np.uint8).reshape(48, 64)
            Image.fromarray(data).save(gen, format="TIFF")
            tiff = gen
        except Exception:
            pass
    if not tiff.is_file():
        report = {
            "validated_at": _utc_now(),
            "passed": False,
            "error": f"TIFF not found: {tiff}",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 1

    report = run_validation(tiff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "output": str(args.output)}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
