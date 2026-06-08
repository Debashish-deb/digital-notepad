"""Phase 14 — adaptive compute profiles and runtime selection."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from omeia.api.compute_profile_service import build_compute_status, detect_compute_profile
from omeia.api.model_runtime_selector import select_runtime


class TestAdaptiveCompute(unittest.TestCase):
    @patch.dict(os.environ, {"OMEIA_ADAPTIVE_COMPUTE": "false"}, clear=False)
    def test_disabled_returns_legacy(self) -> None:
        status = build_compute_status()
        self.assertFalse(status["adaptive_compute_enabled"])
        self.assertEqual(status["profile"], "LEGACY_FIXED")

    @patch.dict(
        os.environ,
        {
            "OMEIA_ADAPTIVE_COMPUTE": "true",
            "OMEIA_LOW_RESOURCE_MODE": "true",
        },
        clear=False,
    )
    def test_low_resource_forces_low_end(self) -> None:
        profile = detect_compute_profile({"host": {"is_linux": True, "linux_workstation_signals": True}})
        self.assertEqual(profile, "LOW_END_LAPTOP")

    @patch.dict(os.environ, {"OMEIA_ADAPTIVE_COMPUTE": "true", "OMEIA_HEAVY_JOBS_REQUIRE_QUEUE": "true"}, clear=False)
    def test_segmentation_queues_on_laptop(self) -> None:
        caps = {
            "host": {"is_linux": False, "linux_workstation_signals": False},
            "imaging": {"streaming_ready": True},
            "docker_worker": {"docker_cli": False},
        }
        with patch("omeia.api.model_runtime_selector.detect_compute_profile", return_value="LOW_END_LAPTOP"):
            route = select_runtime("image_segment", sensitive=True, capabilities=caps)
        self.assertIn(route["runtime"], ("queue", "blocked"))

    @patch.dict(os.environ, {"OMEIA_ADAPTIVE_COMPUTE": "true"}, clear=False)
    def test_sensitive_strategy_never_cloud_by_default(self) -> None:
        with patch("omeia.api.model_runtime_selector.detect_compute_profile", return_value="LOW_END_LAPTOP"):
            route = select_runtime("strategy_report", sensitive=True)
        self.assertNotEqual(route["runtime"], "cloud")

    @patch.dict(os.environ, {"OMEIA_ADAPTIVE_COMPUTE": "false"}, clear=False)
    def test_legacy_runtime_local(self) -> None:
        route = select_runtime("ocr")
        self.assertEqual(route["runtime"], "local")


if __name__ == "__main__":
    unittest.main()
