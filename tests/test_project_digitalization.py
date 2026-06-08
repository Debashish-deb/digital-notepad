"""Acceptance tests for project folder digitalization engine."""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.db_safety import postgres_reachable, resolve_test_postgres_conn

FIXTURE_PROJECT = "digitalization_sample_project"
FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"
PROJECTS = FIXTURES_ROOT  # single project folder parent


class TestProjectDigitalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("PLATFORM_AUTH_DISABLED", "true")
        os.environ["PROJECTS_ROOT"] = str(FIXTURES_ROOT)
        os.environ["LAB_STORAGE_ROOT"] = ""
        os.environ["ENABLE_VECTOR_EMBEDDINGS"] = "false"
        if not postgres_reachable():
            raise unittest.SkipTest(
                "Test database unavailable (set TEST_DATABASE_URL or local POSTGRES_CONN)"
            )
        from omeia.api.project_digitalization_engine import ensure_digitalization_schema

        ensure_digitalization_schema()

    def test_scan_one_project(self) -> None:
        from omeia.api import paths
        from omeia.api.project_digitalization_engine import run_digitalization

        paths.PROJECTS_ROOT = FIXTURES_ROOT
        report = run_digitalization(
            mode="project",
            project_name=FIXTURE_PROJECT,
            max_files=50,
        )
        self.assertIn("counts", report)
        self.assertGreater(report["counts"]["files_scanned"], 0)
        self.assertGreater(report["counts"]["files_processed"], 0)

    @pytest.mark.requires_database
    def test_knowledge_assets_registered_even_on_edge(self) -> None:
        import psycopg
        from omeia.api import paths
        from omeia.api.project_digitalization_engine import run_digitalization

        paths.PROJECTS_ROOT = FIXTURES_ROOT
        run_digitalization(mode="project", project_name=FIXTURE_PROJECT, max_files=50)

        with psycopg.connect(resolve_test_postgres_conn(), connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT count(*) FROM platform.knowledge_assets ka
                    JOIN platform.project_candidates pc ON pc.project_candidate_id = ka.project_candidate_id
                    WHERE pc.project_name = %s;
                    """,
                    (FIXTURE_PROJECT,),
                )
                n = cur.fetchone()[0]
        self.assertGreater(n, 0)

    def test_search_and_review_api(self) -> None:
        from omeia.api.main import app

        client = TestClient(app)
        r = client.get("/api/digitalize/review", params={"kind": "uncategorized", "limit": 5})
        self.assertEqual(r.status_code, 200)
        r2 = client.get("/api/digitalize/search", params={"q": "sample", "limit": 5})
        self.assertEqual(r2.status_code, 200)

    def test_dry_run(self) -> None:
        from omeia.api import paths
        from omeia.api.project_digitalization_engine import run_digitalization

        paths.PROJECTS_ROOT = FIXTURES_ROOT
        report = run_digitalization(mode="project", project_name=FIXTURE_PROJECT, dry_run=True)
        self.assertTrue(report["dry_run"])
        self.assertGreater(report["counts"]["files_scanned"], 0)

    def test_detect_file_types(self) -> None:
        from omeia.api.project_digitalization_engine import detect_file_type

        self.assertEqual(detect_file_type(Path("a.pdf")), "document")
        self.assertEqual(detect_file_type(Path("b.csv")), "spreadsheet")
        self.assertEqual(detect_file_type(Path("c.py")), "script")
        self.assertEqual(detect_file_type(Path("d.log")), "log")


if __name__ == "__main__":
    unittest.main()
