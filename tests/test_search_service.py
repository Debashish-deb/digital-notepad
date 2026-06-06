"""Tests for SearchService copilot retrieval — rerank, gating, intent weights."""
from __future__ import annotations

import unittest

from app_skeleton.api.search_models import SearchHit
from app_skeleton.api.search_service import (
    SearchService,
    _dedup_and_diversify,
    _rerank_hits,
    COPILOT_MIN_SCORE,
)


def _make_hit(
    hit_id: str,
    *,
    bucket: str = "lab",
    title: str = "Title",
    snippet: str = "snippet",
    score: float = 0.5,
) -> SearchHit:
    return SearchHit(
        id=hit_id,
        bucket=bucket,
        title=title,
        snippet=snippet,
        score=score,
        source=bucket,
    )


class TestSearchServiceCopilot(unittest.TestCase):
    def test_reranker_promotes_relevant_chunk(self) -> None:
        query = "MHC class II antigen presentation HGSC"
        hits = [
            _make_hit("a", title="Unrelated file", snippet="general lab storage notes", score=0.82),
            _make_hit(
                "b",
                bucket="research",
                title="MHC class II in HGSC",
                snippet="MHC class II antigen presentation in high-grade serous ovarian cancer",
                score=0.55,
            ),
        ]
        reranked = _rerank_hits(query, hits, top_n=10)
        self.assertEqual(reranked[0].id, "b")
        self.assertGreater(reranked[0].score, reranked[1].score)

    def test_dedup_and_diversify_caps_bucket(self) -> None:
        hits = [
            _make_hit(f"f{i}", bucket="file", snippet=f"unique snippet {i}", score=0.9 - i * 0.01)
            for i in range(6)
        ]
        hits.append(_make_hit("r1", bucket="research", snippet="research snippet", score=0.85))
        diversified = _dedup_and_diversify(hits, limit=5, max_per_bucket=3)
        file_count = sum(1 for h in diversified if h.bucket == "file")
        self.assertLessEqual(file_count, 3)
        self.assertGreaterEqual(len(diversified), 4)

    def test_dedup_skips_identical_snippets(self) -> None:
        hits = [
            _make_hit("a", snippet="same text content here", score=0.9),
            _make_hit("b", snippet="same text content here", score=0.85),
        ]
        diversified = _dedup_and_diversify(hits, limit=5)
        self.assertEqual(len(diversified), 1)

    def test_min_score_gating(self) -> None:
        low = _make_hit("low", score=0.01)
        kept = [h for h in [low] if h.score >= COPILOT_MIN_SCORE]
        self.assertEqual(kept, [])

    def test_hits_for_copilot_accepts_intent(self) -> None:
        svc = SearchService(db_conn="postgresql://invalid:5432/nodb")
        hits = svc.hits_for_copilot(
            "Ashlar stitching",
            intent="protocol_question",
            project_codes=["SPACE"],
            limit=4,
        )
        self.assertIsInstance(hits, list)


if __name__ == "__main__":
    unittest.main()
