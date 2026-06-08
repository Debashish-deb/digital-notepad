"""CyCIF vs Oetlab (wet-lab) document library separation."""
from __future__ import annotations

import unittest

from app_skeleton.api import document_library_service as svc


class CycifWetLabSeparationTest(unittest.TestCase):
    def setUp(self):
        svc.invalidate_cache()

    def _wet_lab_rows(self, filters: dict) -> list[dict]:
        rows = svc.get_enriched_rows()
        wet = [r for r in rows if r.get("section_hint") == "wet_lab_files"]
        hits = svc._apply_filters(wet, q="", domain_tab="wet_lab", system_view=None, filters=filters)
        return [row for _, row in hits]

    def test_oetlab_excludes_cycif_paths(self):
        oetlab = self._wet_lab_rows({"section": "wet_lab_files", "exclude_cycif": True})
        for row in oetlab:
            self.assertFalse(
                svc._is_cycif_path(row.get("logical_path") or ""),
                msg=row.get("logical_path"),
            )

    def test_cycif_only_includes_cycif_paths(self):
        cycif = self._wet_lab_rows({"section": "wet_lab_files", "cycif_only": True})
        self.assertGreater(len(cycif), 0)
        for row in cycif:
            path = (row.get("logical_path") or "").lower()
            self.assertTrue(svc._is_cycif_path(path), msg=row.get("logical_path"))

    def test_no_overlap_between_oetlab_and_cycif(self):
        oetlab_ids = {
            r["asset_id"]
            for r in self._wet_lab_rows({"section": "wet_lab_files", "exclude_cycif": True})
        }
        cycif_ids = {
            r["asset_id"]
            for r in self._wet_lab_rows({"section": "wet_lab_files", "cycif_only": True})
        }
        self.assertFalse(oetlab_ids & cycif_ids)
        self.assertEqual(len(oetlab_ids) + len(cycif_ids), 479)

    def test_cycif_sub_tab_is_subset(self):
        all_cycif = {
            r["asset_id"]
            for r in self._wet_lab_rows({"section": "wet_lab_files", "cycif_only": True})
        }
        projects = {
            r["asset_id"]
            for r in self._wet_lab_rows({
                "section": "wet_lab_files",
                "cycif_only": True,
                "app_page": "cycif.projects",
            })
        }
        self.assertTrue(projects.issubset(all_cycif))
        self.assertGreater(len(projects), 0)


if __name__ == "__main__":
    unittest.main()
