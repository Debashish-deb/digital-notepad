"""Wet-lab document library tab scoping."""
from __future__ import annotations

import unittest

from app_skeleton.api import document_library_service as svc
from app_skeleton.api.library_taxonomy import describe_nav_scope, resolve_preset_from_nav


class WetLabDocumentFiltersTest(unittest.TestCase):
    def setUp(self):
        svc.invalidate_cache()

    def test_nav_presets_differ_by_sub_tab(self):
        files = resolve_preset_from_nav("wet_lab", "files")
        protocols = resolve_preset_from_nav("wet_lab", "protocols")
        inventory = resolve_preset_from_nav("wet_lab", "inventory")
        self.assertEqual(files["filters"], {"section": "wet_lab_files", "exclude_cycif": True})
        self.assertEqual(protocols["filters"], {"section": "wet_lab_files", "protocol_only": True, "exclude_cycif": True})
        self.assertEqual(inventory["filters"], {"section": "wet_lab_files", "reagents_only": True, "exclude_cycif": True})

    def test_wet_lab_tab_counts_are_distinct(self):
        rows = svc.get_enriched_rows()
        wet = [r for r in rows if r.get("section_hint") == "wet_lab_files"]

        def count(filters):
            return len(svc._apply_filters(wet, q="", domain_tab="wet_lab", system_view=None, filters=filters))

        all_count = count({"section": "wet_lab_files", "exclude_cycif": True})
        proto_count = count({"section": "wet_lab_files", "protocol_only": True, "exclude_cycif": True})
        reag_count = count({"section": "wet_lab_files", "reagents_only": True, "exclude_cycif": True})
        spatial_count = count({
            "section": "wet_lab_files",
            "protocol_only": True,
            "exclude_cycif": True,
            "protocol_category": "proto_spatial",
        })

        self.assertGreater(all_count, proto_count)
        self.assertGreater(all_count, reag_count)
        self.assertGreater(proto_count, spatial_count)
        self.assertGreater(proto_count, 0)
        self.assertGreater(reag_count, 0)

    def test_describe_nav_scope_for_protocols(self):
        scope = describe_nav_scope("wet_lab", "protocols")
        self.assertIsNotNone(scope)
        self.assertIn("protocol_only", scope["filters"])
        self.assertIn("is_protocol", scope["scope_summary"])


if __name__ == "__main__":
    unittest.main()
