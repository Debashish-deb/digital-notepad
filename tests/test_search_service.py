"""Tests for SearchService copilot retrieval — rerank, gating, intent weights."""
from __future__ import annotations

import unittest

from omeia.api.search_models import SearchHit
from omeia.api.search_service import (
    COPILOT_MIN_SCORE,
    INTENT_BUCKET_CAPS,
    SearchService,
    _copilot_include_restricted,
    _dedup_and_diversify,
    _project_research_query,
    _rerank_hits,
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

    def test_project_question_research_cap_raised(self) -> None:
        caps = INTENT_BUCKET_CAPS["project_question"]
        self.assertGreaterEqual(caps.get("research", 0), 4)

    def test_copilot_include_restricted_for_lab_roles(self) -> None:
        self.assertTrue(_copilot_include_restricted("admin"))
        self.assertTrue(_copilot_include_restricted("editor"))
        self.assertTrue(_copilot_include_restricted("researcher"))
        self.assertFalse(_copilot_include_restricted("viewer"))
        self.assertFalse(_copilot_include_restricted(None))

    def test_project_research_query_enriches_code(self) -> None:
        enriched = _project_research_query("tell me about the project", ["EyeMT"])
        self.assertEqual(enriched, "EyeMT tell me about the project")
        unchanged = _project_research_query("tell more about EyeMT project", None)
        self.assertEqual(unchanged, "tell more about EyeMT project")


if __name__ == "__main__":
    unittest.main()
