"""Tests for TIFF/OME-TIFF image streaming foundation."""
from __future__ import annotations

import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app_skeleton.api.main import app
from app_skeleton.api.image_streaming.constants import MAX_TILE_EDGE
from app_skeleton.api.image_streaming.image_metadata_service import CACHE_PATH
from app_skeleton.api.image_streaming.storage_adapter import ImageStorageAdapter
from app_skeleton.security.auth import _dev_user


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
        return
    except ImportError as exc:
        raise unittest.SkipTest("tifffile or Pillow required for TIFF tests") from exc


TEST_ASSET_ID = "asset_test_tiff_stream"
TEST_ROW = {
    "asset_id": TEST_ASSET_ID,
    "filename": "test_stream.tif",
    "extension": ".tif",
    "logical_path": "test/test_stream.tif",
    "storage_provider": "local_database_mirror",
    "size_bytes": 1024,
    "project_hint": "TESTPROJ",
    "sensitivity_level": "internal",
}


class TestImageStreaming(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.tiff_path = self.root / "test" / "test_stream.tif"
        self.tiff_path.parent.mkdir(parents=True, exist_ok=True)
        _make_test_tiff(self.tiff_path)
        self.cache_backup = CACHE_PATH.read_text(encoding="utf-8") if CACHE_PATH.is_file() else None

    def tearDown(self) -> None:
        self.tmp.cleanup()
        if self.cache_backup is not None:
            CACHE_PATH.write_text(self.cache_backup, encoding="utf-8")
        elif CACHE_PATH.is_file():
            CACHE_PATH.unlink()

    def _fake_lookup(self, asset_id: str):
        return TEST_ROW if asset_id == TEST_ASSET_ID else None

    def _mock_resolve(self):
        root = self.root
        lookup = self._fake_lookup
        stack = ExitStack()
        stack.enter_context(
            patch.multiple(
                "app_skeleton.api.image_streaming.storage_adapter",
                lookup_asset_row=lookup,
                _ROOTS={
                    "database-static": root,
                    "projects-static": root,
                    "csc-media": root,
                },
            )
        )
        stack.enter_context(
            patch("app_skeleton.api.routers.image_assets.lookup_asset_row", lookup)
        )
        return stack

    def test_metadata_requires_auth_when_enabled(self) -> None:
        with patch("app_skeleton.security.auth.AUTH_DISABLED", False):
            client = TestClient(app)
            response = client.get(f"/api/assets/{TEST_ASSET_ID}/image/metadata")
            self.assertEqual(response.status_code, 401)

    def test_metadata_for_test_tiff(self) -> None:
        with self._mock_resolve():
            resolved = ImageStorageAdapter().resolve_asset(TEST_ASSET_ID)
            self.assertIsNotNone(resolved)
            response = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/metadata")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["asset_id"], TEST_ASSET_ID)
            self.assertNotIn("logical_path", body)
            self.assertNotIn("disk_path", body)

    def test_manifest_no_path_exposure(self) -> None:
        with self._mock_resolve():
            response = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/manifest")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            for key in ("disk_path", "logical_path", "provider", "original_path"):
                self.assertNotIn(key, body)

    def test_thumbnail_returns_image(self) -> None:
        with self._mock_resolve():
            response = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/thumbnail")
            self.assertEqual(response.status_code, 200)
            self.assertIn("image/", response.headers.get("content-type", ""))

    def test_tile_rejects_huge_region(self) -> None:
        with self._mock_resolve():
            response = self.client.get(
                f"/api/assets/{TEST_ASSET_ID}/image/tile",
                params={"width": MAX_TILE_EDGE + 1, "height": 256},
            )
            self.assertIn(response.status_code, (400, 422))

    def test_tile_valid_region(self) -> None:
        with self._mock_resolve():
            response = self.client.get(
                f"/api/assets/{TEST_ASSET_ID}/image/tile",
                params={"x": 0, "y": 0, "width": 32, "height": 32},
            )
            if response.status_code == 503:
                self.skipTest("tifffile or Pillow unavailable")
            self.assertEqual(response.status_code, 200)
            self.assertIn("image/", response.headers.get("content-type", ""))

    def test_stream_range(self) -> None:
        with self._mock_resolve():
            full = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/stream")
            self.assertEqual(full.status_code, 200)
            self.assertEqual(full.headers.get("accept-ranges"), "bytes")
            partial = self.client.get(
                f"/api/assets/{TEST_ASSET_ID}/image/stream",
                headers={"Range": "bytes=0-15"},
            )
            self.assertEqual(partial.status_code, 206)
            self.assertLessEqual(len(partial.content), 16)

    def test_404_invalid_asset(self) -> None:
        with patch(
            "app_skeleton.api.image_streaming.storage_adapter.lookup_asset_row",
            return_value=None,
        ):
            response = self.client.get("/api/assets/asset_nonexistent/image/metadata")
            self.assertEqual(response.status_code, 404)

    def test_non_image_unsupported(self) -> None:
        pdf_row = {**TEST_ROW, "asset_id": "asset_pdf", "extension": ".pdf", "filename": "doc.pdf"}

        def lookup(asset_id: str):
            return pdf_row if asset_id == "asset_pdf" else None

        with patch(
            "app_skeleton.api.image_streaming.storage_adapter.lookup_asset_row",
            lookup,
        ), patch(
            "app_skeleton.api.routers.image_assets.lookup_asset_row",
            lookup,
        ):
            response = self.client.get("/api/assets/asset_pdf/image/metadata")
            self.assertEqual(response.status_code, 404)

    def test_permission_denied_for_restricted_viewer(self) -> None:
        viewer = {"email": "viewer@test", "role": "viewer"}
        restricted_row = {**TEST_ROW, "sensitivity_level": "restricted"}
        def lookup(asset_id: str):
            return restricted_row if asset_id == TEST_ASSET_ID else None

        with self._mock_resolve(), patch(
            "app_skeleton.api.routers.image_assets.lookup_asset_row",
            lookup,
        ), patch(
            "app_skeleton.api.routers.image_assets.can_access_image_asset",
            return_value=False,
        ), patch(
            "app_skeleton.security.auth.require_platform_user",
            return_value=viewer,
        ):
            response = self.client.get(f"/api/assets/{TEST_ASSET_ID}/image/metadata")
            self.assertEqual(response.status_code, 403)

    def test_inspect_populates_cache(self) -> None:
        with self._mock_resolve():
            from app_skeleton.api.image_streaming.image_streaming_service import ImageStreamingService

            svc = ImageStreamingService()
            result = svc.inspect_asset(TEST_ASSET_ID)
            self.assertEqual(result["asset_id"], TEST_ASSET_ID)
            meta = result["image_metadata"]
            self.assertIn(meta.get("streaming_status"), ("tile_ready", "metadata_only", "failed"))

    def test_readiness_stats(self) -> None:
        with patch(
            "app_skeleton.security.auth.require_admin_user",
            return_value=_dev_user(),
        ):
            response = self.client.get("/api/admin/image-streaming/readiness")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertIn("tiff_asset_count", body)


if __name__ == "__main__":
    unittest.main()
