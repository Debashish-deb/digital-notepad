"""Vault semantic search reliability — Postgres filters, enrichment, dedupe (mock-heavy)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from tests.auth_fixtures import auth_override

from app_skeleton.api.search_models import SearchHit
from app_skeleton.api.search_service import _suppress_checksum_duplicates
from app_skeleton.api.raw_vault_store import (
    _is_vault_row_active,
    _search_vault_json,
    _vault_active_sql_clauses,
)
from app_skeleton.api.vault_vector_search import filter_and_enrich_vault_vector_hits


class TestVaultActiveFilters(unittest.TestCase):
    def test_sql_clauses_exclude_duplicate_and_inactive(self) -> None:
        clauses = _vault_active_sql_clauses(table="v")
        joined = " ".join(clauses)
        self.assertIn("duplicate_status", joined)
        self.assertIn("inventory_active", joined)
        self.assertIn("!= 'duplicate'", joined)

    def test_row_active_rejects_duplicate_and_inactive(self) -> None:
        self.assertFalse(_is_vault_row_active({"metadata_json": {"duplicate_status": "duplicate"}}))
        self.assertFalse(_is_vault_row_active({"metadata_json": {"inventory_active": "false"}}))
        self.assertTrue(_is_vault_row_active({"metadata_json": {"duplicate_status": "unique"}}))

    def test_json_search_skips_inactive_rows(self) -> None:
        rows = [
            {"asset_id": "a1", "filename": "keep.pdf", "logical_path": "x/keep.pdf", "metadata_json": {}},
            {
                "asset_id": "a2",
                "filename": "dup.pdf",
                "logical_path": "x/dup.pdf",
                "metadata_json": {"duplicate_status": "duplicate"},
            },
            {
                "asset_id": "a3",
                "filename": "off.pdf",
                "logical_path": "x/off.pdf",
                "metadata_json": {"inventory_active": "no"},
            },
        ]
        with patch("app_skeleton.api.raw_vault_store.load_inventory_rows", return_value=rows):
            hits = _search_vault_json(
                "keep",
                domain=None,
                project_hint=None,
                review_status=None,
                vector_status=None,
                extraction_status=None,
                uncategorized_only=False,
                limit=10,
            )
        ids = {h["asset_id"] for h in hits}
        self.assertEqual(ids, {"a1"})


class TestVaultVectorEnrichment(unittest.TestCase):
    def test_filter_enriches_and_drops_inactive(self) -> None:
        hits = [
            {"asset_id": "good", "score": 0.9, "excerpt": "text", "metadata": {}},
            {"asset_id": "dup", "score": 0.8, "excerpt": "dup", "metadata": {}},
            {"asset_id": "missing", "score": 0.7, "excerpt": "gone", "metadata": {}},
        ]
        assets = {
            "good": {
                "asset_id": "good",
                "filename": "good.pdf",
                "logical_path": "lab/good.pdf",
                "checksum_sha256": "abc",
                "review_status": "reviewed",
                "metadata_json": {},
            },
            "dup": {
                "asset_id": "dup",
                "filename": "dup.pdf",
                "logical_path": "lab/dup.pdf",
                "checksum_sha256": "def",
                "metadata_json": {"duplicate_status": "duplicate"},
            },
        }
        with patch(
            "app_skeleton.api.vault_vector_search.fetch_vault_assets_by_ids",
            return_value=assets,
        ), patch(
            "app_skeleton.api.vault_vector_search.vault_postgres_reachable",
            return_value=True,
        ):
            enriched = filter_and_enrich_vault_vector_hits(hits)

        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0]["asset_id"], "good")
        self.assertEqual(enriched[0]["filename"], "good.pdf")
        self.assertEqual(enriched[0]["checksum_sha256"], "abc")
        self.assertEqual(enriched[0]["metadata"]["checksum_sha256"], "abc")


class TestChecksumCrossBucketDedupe(unittest.TestCase):
    def test_keeps_highest_score_per_checksum(self) -> None:
        hits = [
            SearchHit(
                id="v1",
                bucket="vault",
                title="Vault copy",
                snippet="s",
                score=0.4,
                source="vault",
                metadata={"asset_id": "v1"},
            ),
            SearchHit(
                id="f1",
                bucket="file",
                title="File copy",
                snippet="s",
                score=0.9,
                source="file",
                metadata={"asset_id": "f1"},
            ),
        ]
        assets = {
            "v1": {"checksum_sha256": "same-hash"},
            "f1": {"checksum_sha256": "same-hash"},
        }
        with patch("app_skeleton.api.search_service.fetch_vault_assets_by_ids", return_value=assets):
            deduped = _suppress_checksum_duplicates(hits)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].id, "f1")
        self.assertEqual(deduped[0].score, 0.9)


class TestVectorIndexerPayload(unittest.TestCase):
    def test_upsert_includes_filename_path_checksum(self) -> None:
        captured: list[dict] = []

        def _capture(client, points_data, **kwargs):
            captured.extend(points_data)
            return len(points_data)

        with patch("app_skeleton.api.vector_indexer.upsert_text_chunks", side_effect=_capture):
            from app_skeleton.api.vector_indexer import upsert_vault_asset_chunks

            n = upsert_vault_asset_chunks(
                MagicMock(),
                "asset-1",
                [{"text": "sample chunk text for indexing", "chunk_index": 0}],
                source_path="/data/file.pdf",
                filename="file.pdf",
                logical_path="lab/file.pdf",
                checksum_sha256="sha256-abc",
            )
        self.assertEqual(n, 1)
        payload = captured[0]["payload"]
        self.assertEqual(payload["filename"], "file.pdf")
        self.assertEqual(payload["logical_path"], "lab/file.pdf")
        self.assertEqual(payload["checksum_sha256"], "sha256-abc")


class TestVaultApiSemanticMerge(unittest.TestCase):
    def test_vault_search_merges_semantic_hits(self) -> None:
        from app_skeleton.api.main import app

        metadata_hit = {"asset_id": "meta-1", "filename": "meta.pdf", "logical_path": "x/meta.pdf"}
        semantic_hit = {
            "asset_id": "sem-1",
            "filename": "sem.pdf",
            "logical_path": "x/sem.pdf",
            "checksum_sha256": "chk",
            "excerpt": "semantic excerpt",
            "score": 0.88,
        }
        with auth_override("researcher"), patch(
            "app_skeleton.api.routers.vault.search_vault",
            return_value=[metadata_hit],
        ), patch(
            "app_skeleton.api.platform_flags.vectorization_enabled",
            return_value=True,
        ), patch(
            "app_skeleton.api.vault_vector_search.search_vault_vectors",
            return_value=[semantic_hit],
        ):
            client = TestClient(app)
            res = client.get("/api/vault/search", params={"q": "protocol", "semantic": True})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        ids = {r.get("asset_id") for r in body.get("results") or []}
        self.assertEqual(ids, {"meta-1", "sem-1"})
        engines = {e.get("engine") for e in body.get("engines") or []}
        self.assertIn("postgres_metadata", engines)
        self.assertIn("qdrant_semantic", engines)


if __name__ == "__main__":
    unittest.main()
