"""Phase 1 vault upsert via vector_indexer."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app_skeleton.api.vector_indexer import upsert_vault_asset_chunks


def test_upsert_vault_asset_chunks_builds_points() -> None:
    client = MagicMock()
    chunks = [{"text": "A long enough vault chunk for embedding.", "chunk_index": 0}]
    with patch("app_skeleton.api.vector_indexer.upsert_text_chunks", return_value=1) as mock_upsert:
        n = upsert_vault_asset_chunks(client, "asset_abc", chunks, source_path="/lab/file.pdf")
        assert n == 1
        mock_upsert.assert_called_once()
        args, kwargs = mock_upsert.call_args
        assert kwargs.get("kind") == "vault" or args[1][0]["chunk_uid"].startswith("asset_abc:")
