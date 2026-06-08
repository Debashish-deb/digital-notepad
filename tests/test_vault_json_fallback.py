"""Phase 1 VAULT_JSON_FALLBACK behavior."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from omeia.api.raw_vault_store import search_vault


def test_search_vault_skips_json_when_fallback_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VAULT_JSON_FALLBACK", "false")
    with patch("omeia.api.raw_vault_store._search_vault_postgres", return_value=[]):
        with patch("omeia.api.raw_vault_store._search_vault_json") as mock_json:
            hits = search_vault("test query")
            assert hits == []
            mock_json.assert_not_called()


def test_search_vault_uses_json_when_fallback_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VAULT_JSON_FALLBACK", "true")
    with patch("omeia.api.raw_vault_store._search_vault_postgres", return_value=[]):
        with patch(
            "omeia.api.raw_vault_store._search_vault_json",
            return_value=[{"asset_id": "a1", "filename": "f.txt"}],
        ) as mock_json:
            with patch(
                "omeia.api.raw_vault_store._sanitize_metadata_in_rows",
                side_effect=lambda rows: rows,
            ):
                hits = search_vault("test query")
                mock_json.assert_called_once()
                assert len(hits) == 1
