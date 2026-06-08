"""Unit tests for pytest database safety guards."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from tests import db_safety as ds


class TestDbSafety(unittest.TestCase):
    def test_resolve_prefers_test_database_url(self) -> None:
        ds.resolve_test_postgres_conn.cache_clear()
        ds.postgres_reachable.cache_clear()
        with patch.dict(
            os.environ,
            {
                "TEST_DATABASE_URL": "postgresql://test@localhost:5432/testdb",
                "POSTGRES_CONN": "postgresql://other@localhost:5432/other",
                "SUPABASE_DB_PASSWORD": "secret",
            },
            clear=False,
        ):
            self.assertEqual(
                ds.resolve_test_postgres_conn(),
                "postgresql://test@localhost:5432/testdb",
            )

    def test_production_host_detection(self) -> None:
        self.assertTrue(ds.looks_like_production_supabase(
            "postgresql://postgres.x@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
        ))
        self.assertFalse(ds.looks_like_production_supabase(
            "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai"
        ))

    def test_supabase_config_uses_test_resolver_in_pytest(self) -> None:
        from omeia.api import supabase_config as sc

        with patch.dict(
            os.environ,
            {
                "OMEIA_PYTEST": "1",
                "TEST_DATABASE_URL": "postgresql://pytest@localhost:5432/pytest",
                "SUPABASE_DB_PASSWORD": "must-be-ignored",
            },
            clear=False,
        ):
            self.assertEqual(sc.postgres_conn(), "postgresql://pytest@localhost:5432/pytest")


if __name__ == "__main__":
    unittest.main()
