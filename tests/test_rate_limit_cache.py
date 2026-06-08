"""Tests for copilot rate limiting headers and retrieval cache key separation."""
from __future__ import annotations

import os
import unittest

from app_skeleton.api.rate_limit import check_rate_limit
from app_skeleton.api.retrieval_cache import (
    clear_cache,
    make_cache_key,
    set_cached,
    should_cache,
)


class TestRateLimitAndCache(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["COPILOT_RATE_LIMIT_PER_MINUTE"] = "3"
        os.environ["COPILOT_RATE_LIMIT_WINDOW_SEC"] = "60"
        os.environ["RETRIEVAL_CACHE_ENABLED"] = "true"
        clear_cache()

    def test_rate_limit_headers_present(self) -> None:
        allowed, headers = check_rate_limit(user_id="user@test", ip_address="127.0.0.1")
        self.assertTrue(allowed)
        self.assertIn("X-RateLimit-Limit", headers)
        self.assertIn("X-RateLimit-Remaining", headers)
        self.assertIn("X-RateLimit-Reset", headers)
        self.assertEqual(headers["X-RateLimit-Limit"], "3")

    def test_rate_limit_blocks_after_quota(self) -> None:
        for _ in range(3):
            allowed, _ = check_rate_limit(user_id="quota-user", ip_address="10.0.0.1")
            self.assertTrue(allowed)
        allowed, headers = check_rate_limit(user_id="quota-user", ip_address="10.0.0.1")
        self.assertFalse(allowed)
        self.assertEqual(headers["X-RateLimit-Remaining"], "0")

    def test_cache_key_separates_users_and_roles(self) -> None:
        key_a = make_cache_key(
            query="Ashlar",
            scopes="lab",
            mode="hybrid",
            user_id="alice@test",
            user_role="researcher",
            project_codes=["SPACE"],
            filters={"section_id": "wet_lab_files"},
            include_restricted=False,
        )
        key_b = make_cache_key(
            query="Ashlar",
            scopes="lab",
            mode="hybrid",
            user_id="bob@test",
            user_role="admin",
            project_codes=["SPACE"],
            filters={"section_id": "wet_lab_files"},
            include_restricted=False,
        )
        self.assertNotEqual(key_a, key_b)

    def test_restricted_content_not_cached_across_users(self) -> None:
        self.assertFalse(should_cache(include_restricted=True, user_role="admin"))
        self.assertFalse(
            should_cache(
                include_restricted=False,
                user_role="researcher",
                hits=[{"visibility_level": "confidential"}],
            )
        )

    def test_cache_roundtrip(self) -> None:
        key = make_cache_key(
            query="test query",
            scopes="lab",
            mode="hybrid",
            user_id="u1",
            user_role="viewer",
            project_codes=[],
            filters={},
            include_restricted=False,
        )
        set_cached(key, {"query": "test query", "total": 0, "hits": []})
        from app_skeleton.api.retrieval_cache import get_cached

        cached = get_cached(key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.get("query"), "test query")


if __name__ == "__main__":
    unittest.main()
