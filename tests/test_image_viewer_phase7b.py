"""Phase 7B — research imaging viewer extensions."""
from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from omeia.api.main import app
from omeia.api.image_streaming.image_metadata_service import CACHE_PATH
from omeia.api.image_streaming.image_viewer_store import STORE_PATH, _save_json_store
from omeia.api.image_streaming.storage_adapter import ImageStorageAdapter
from omeia.security.auth import _dev_user

TEST_ASSET_ID = "asset_test_viewer_7b"
TEST_ROW = {
    "asset_id": TEST_ASSET_ID,
    "filename": "test_viewer.tif",
    "extension": ".tif",
    "logical_path": "test/test_viewer.tif",
    "storage_provider": "local_database_mirror",
    "size_bytes": 1024,
    "project_hint": "TESTPROJ",
    "sensitivity_level": "internal",
}


def _make_test_tiff(path: Path, width: int = 64, height: int = 48) -> None:
    try:
        import numpy as np  # type: ignore
        import tifffile  # type: ignore

        data = np.linspace(0, 255, width * height, dtype=np.uint8).reshape(height, width)
        tifffile.imwrite(str(path), data)
        return
    except ImportError:
        pass
    try:
        from PIL import Image

        im = Image.new("L", (width, height))
        im.save(path, format="TIFF")
    except ImportError as exc:
        raise unittest.SkipTest("tifffile or Pillow required") from exc


class TestImageViewerPhase7B(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.tiff_path = self.root / "test" / "test_viewer.tif"
        self.tiff_path.parent.mkdir(parents=True, exist_ok=True)
        _make_test_tiff(self.tiff_path)
        self.cache_backup = CACHE_PATH.read_text(encoding="utf-8") if CACHE_PATH.is_file() else None
        self.store_backup = STORE_PATH.read_text(encoding="utf-8") if STORE_PATH.is_file() else None
        _save_json_store({"rois": [], "overlays": [], "presets": []})

    def tearDown(self) -> None:
        self.tmp.cleanup()
        if self.cache_backup is not None:
            CACHE_PATH.write_text(self.cache_backup, encoding="utf-8")
        elif CACHE_PATH.is_file():
            CACHE_PATH.unlink()
        if self.store_backup is not None:
            STORE_PATH.write_text(self.store_backup, encoding="utf-8")
        elif STORE_PATH.is_file():
            STORE_PATH.unlink()

    def _fake_lookup(self, asset_id: str):
        return TEST_ROW if asset_id == TEST_ASSET_ID else None

    def _mock_resolve(self):
        root = self.root
        lookup = self._fake_lookup
        stack = ExitStack()
        stack.enter_context(
            patch.multiple(
                "omeia.api.image_streaming.storage_adapter",
                lookup_asset_row=lookup,
                _ROOTS={
                    "database-static": root,
                    "projects-static": root,
                    "csc-media": root,
                },
            )
        )
        stack.enter_context(patch("omeia.api.routers.image_assets.lookup_asset_row", lookup))
        stack.enter_context(patch("omeia.api.routers.image_viewer.lookup_asset_row", lookup))
        stack.enter_context(
            patch(
                "omeia.api.image_streaming.image_viewer_store._db_available",
                return_value=False,
            )
        )
        return stack

    def test_manifest_includes_viewer_flags_and_channel_names(self) -> None:
        with self._mock_resolve():
            response = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/manifest")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertIn("viewer_flags", body)
            self.assertIn("channel_names", body)
            flags = body["viewer_flags"]
            self.assertIn("low_resource_mode", flags)
            self.assertIn("heatmaps", flags)
            self.assertIn("segmentation_overlays", flags)
            self.assertIn("roi_annotations", flags)

    def test_roi_create_list_delete(self) -> None:
        with self._mock_resolve(), patch(
            "omeia.security.auth.require_platform_user",
            return_value=_dev_user(),
        ):
            create = self.client.post(
                f"/api/assets/{TEST_ASSET_ID}/image/rois",
                json={
                    "name": "Tumor core",
                    "geometry": {"x": 10, "y": 20, "width": 100, "height": 80},
                    "roi_type": "rectangle",
                    "tags": ["tumor"],
                },
            )
            self.assertEqual(create.status_code, 200)
            roi_id = create.json()["roi"]["roi_id"]

            listed = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/rois")
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(len(listed.json()["rois"]), 1)

            deleted = self.client.delete(f"/api/assets/{TEST_ASSET_ID}/image/rois/{roi_id}")
            self.assertEqual(deleted.status_code, 200)

            listed2 = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/rois")
            self.assertEqual(len(listed2.json()["rois"]), 0)

    def test_overlay_list_and_create(self) -> None:
        with self._mock_resolve(), patch(
            "omeia.security.auth.require_platform_user",
            return_value=_dev_user(),
        ):
            empty = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/overlays")
            self.assertEqual(empty.status_code, 200)
            self.assertEqual(empty.json()["overlays"], [])

            created = self.client.post(
                f"/api/assets/{TEST_ASSET_ID}/image/overlays",
                json={
                    "overlay_asset_id": "asset_overlay_seg",
                    "overlay_type": "stardist",
                    "label": "Nuclei",
                },
            )
            self.assertEqual(created.status_code, 200)
            listed = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/overlays")
            self.assertEqual(len(listed.json()["overlays"]), 1)

    def test_channel_preset_save_load_delete(self) -> None:
        with patch(
            "omeia.security.auth.require_platform_user",
            return_value=_dev_user(),
        ), patch(
            "omeia.api.image_streaming.image_viewer_store._db_available",
            return_value=False,
        ):
            saved = self.client.post(
                "/api/users/me/image/channel-presets",
                json={"name": "My panel", "channels": [{"index": 0, "visible": True, "color": "#fff"}]},
            )
            self.assertEqual(saved.status_code, 200)
            preset_id = saved.json()["preset"]["preset_id"]

            listed = self.client.get("/api/users/me/image/channel-presets")
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(len(listed.json()["presets"]), 1)

            deleted = self.client.delete(f"/api/users/me/image/channel-presets/{preset_id}")
            self.assertEqual(deleted.status_code, 200)

    def test_cell_inspection_endpoint(self) -> None:
        with self._mock_resolve(), patch(
            "omeia.security.auth.require_platform_user",
            return_value=_dev_user(),
        ):
            response = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/cells/cell_42")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["cell_id"], "cell_42")
            self.assertIn("area_um2", body)
            self.assertIn("centroid", body)

    def test_histogram_endpoint(self) -> None:
        with self._mock_resolve(), patch(
            "omeia.security.auth.require_platform_user",
            return_value=_dev_user(),
        ):
            response = self.client.get(
                f"/api/assets/{TEST_ASSET_ID}/image/histogram",
                params={"width": 32, "height": 32},
            )
            if response.status_code == 503:
                self.skipTest("tifffile unavailable")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertIn("counts", body)
            self.assertEqual(len(body["counts"]), body["bins"])

    def test_asset_authorization_403(self) -> None:
        with self._mock_resolve(), patch(
            "omeia.api.routers.image_viewer.can_access_image_asset",
            return_value=False,
        ), patch(
            "omeia.security.auth.require_platform_user",
            return_value={"email": "viewer@test", "role": "viewer"},
        ):
            response = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/rois")
            self.assertEqual(response.status_code, 403)

    def test_ome_channel_metadata_parsing(self) -> None:
        from omeia.api.image_streaming.image_metadata_service import (
            _parse_ome_channel_names,
            _parse_ome_pixel_size_um,
        )

        xml = """
        <OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">
          <Image><Pixels PhysicalSizeX="0.325" DimensionOrder="XYCZT">
            <Channel Name="DAPI" /><Channel Name="CD3" />
          </Pixels></Image>
        </OME>
        """
        names = _parse_ome_channel_names(xml)
        self.assertIn("DAPI", names)
        self.assertIn("CD3", names)
        self.assertAlmostEqual(_parse_ome_pixel_size_um(xml), 0.325)

    def test_measurement_helpers(self) -> None:
        from omeia.api.image_streaming.measurement_helpers import (
            pixels_to_microns,
            polygon_area,
            rectangle_area,
        )

        self.assertAlmostEqual(pixels_to_microns(10, 0.5), 5.0)
        self.assertAlmostEqual(rectangle_area({"width": 10, "height": 5}), 50)
        area = polygon_area([{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}, {"x": 0, "y": 10}])
        self.assertAlmostEqual(area, 100)

    def test_inspect_populates_channel_names_field(self) -> None:
        with self._mock_resolve():
            from omeia.api.image_streaming.image_streaming_service import ImageStreamingService

            svc = ImageStreamingService()
            result = svc.inspect_asset(TEST_ASSET_ID)
            meta = result["image_metadata"]
            self.assertIn("channel_names", meta)
            self.assertIn("physical_pixel_size_um", meta)


if __name__ == "__main__":
    unittest.main()
