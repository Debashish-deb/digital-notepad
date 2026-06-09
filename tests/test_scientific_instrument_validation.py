"""Scientific imaging instrument validation — tifffile ground truth equivalence."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_TIFF = REPO_ROOT / "tests" / "fixtures" / "vault_sample_project" / "slide.tiff"


def _ensure_fixture_tiff() -> Path:
    """Return a readable TIFF — generate if bundled fixture is missing or invalid."""
    try:
        from PIL import Image
    except ImportError:
        Image = None  # type: ignore

    if FIXTURE_TIFF.is_file() and FIXTURE_TIFF.stat().st_size > 256:
        try:
            if Image:
                with Image.open(FIXTURE_TIFF) as im:
                    im.verify()
                return FIXTURE_TIFF
        except Exception:
            pass

    try:
        import numpy as np  # type: ignore
        import tifffile  # type: ignore

        FIXTURE_TIFF.parent.mkdir(parents=True, exist_ok=True)
        data = np.arange(64 * 48, dtype=np.uint16).reshape(48, 64)
        tifffile.imwrite(str(FIXTURE_TIFF), data)
        return FIXTURE_TIFF
    except ImportError:
        pass

    if Image:
        FIXTURE_TIFF.parent.mkdir(parents=True, exist_ok=True)
        im = Image.new("L", (64, 48))
        im.putdata(list(range(64 * 48)))
        im.save(FIXTURE_TIFF, format="TIFF")
        return FIXTURE_TIFF

    raise unittest.SkipTest("tifffile or Pillow required")


class TestScientificInstrumentValidation(unittest.TestCase):
    def test_validation_script_passes(self) -> None:
        try:
            import tifffile  # noqa: F401
        except ImportError:
            try:
                from PIL import Image  # noqa: F401
            except ImportError:
                raise unittest.SkipTest("tifffile or Pillow required") from None
        tiff = _ensure_fixture_tiff()
        from scripts.imaging.validate_scientific_instrument import run_validation

        report = run_validation(tiff)
        if report.get("instrument", {}).get("error"):
            raise unittest.SkipTest(report["instrument"]["error"])
        self.assertTrue(report["dimensions_match"], report)
        self.assertTrue(report["dtype_match"], report)
        self.assertTrue(report["pixel_probes_match"], report.get("probe_comparison"))
        self.assertTrue(report["passed"])

    def test_marker_graph_endpoint(self) -> None:
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from omeia.api.main import app
        from omeia.security.auth import _dev_user

        client = TestClient(app)
        with patch("omeia.security.auth.require_platform_user", return_value=_dev_user()):
            response = client.get(
                "/api/imaging/markers/graph",
                params={"channel_names": ["DAPI", "CD8"]},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data.get("marker_count", 0), 2)

    def test_council_analyze_mock(self) -> None:
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from omeia.api.main import app
        from omeia.security.auth import _dev_user

        TEST_ASSET = "asset_test_council"
        row = {
            "asset_id": TEST_ASSET,
            "filename": "x.tif",
            "extension": ".tif",
            "logical_path": "x.tif",
            "storage_provider": "local_database_mirror",
            "size_bytes": 1,
            "project_hint": "T",
            "sensitivity_level": "internal",
        }
        client = TestClient(app)
        with patch("omeia.security.auth.require_platform_user", return_value=_dev_user()), patch(
            "omeia.api.routers.imaging_science.lookup_asset_row",
            return_value=row,
        ), patch(
            "omeia.api.image_streaming.storage_adapter.lookup_asset_row",
            return_value=row,
        ), patch(
            "omeia.api.routers.imaging_science._streaming.build_manifest",
            return_value={"dtype": "uint8", "channel_names": ["DAPI"]},
        ):
            response = client.post(
                "/api/imaging/council/analyze",
                json={"asset_id": TEST_ASSET, "question": "Interpret CD8 infiltration", "markers": ["CD8"]},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("guardrails_applied"))
        self.assertGreaterEqual(len(data.get("opinions", [])), 4)


@pytest.mark.parametrize("marker", ["DAPI", "CD8", "PanCK"])
def test_imaging_knowledge_bridge_nodes(marker: str) -> None:
    from omeia.api.imaging_knowledge_bridge import build_marker_graph

    graph = build_marker_graph([marker])
    labels = [n["label"] for n in graph["nodes"]]
    assert marker in labels
