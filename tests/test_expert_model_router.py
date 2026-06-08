"""Tests for Layer 3 expert model routing."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from omeia.api.chat_intent import classify_chat_intent
from omeia.api.chat_conversation import enrich_intent_decision
from omeia.api.expert_model_router import (
    is_conversation_only_intent,
    resolve_expert_model,
)


class TestExpertModelRouter(unittest.TestCase):
    def test_greeting_is_conversation_only(self) -> None:
        decision = enrich_intent_decision(classify_chat_intent("hi"), "hi")
        self.assertTrue(is_conversation_only_intent(decision))

    @patch.dict(os.environ, {"OMEIA_EXPERT_ROUTING_ENABLED": "true"}, clear=False)
    def test_greeting_routes_conversation_model(self) -> None:
        decision = enrich_intent_decision(classify_chat_intent("how are you doing today?"), "how are you doing today?")
        route = resolve_expert_model(decision, "how are you doing today?")
        self.assertIsNotNone(route)
        self.assertEqual(route.layer, "conversation")

    @patch.dict(os.environ, {"OMEIA_EXPERT_ROUTING_ENABLED": "true"}, clear=False)
    def test_oncology_question_routes_expert(self) -> None:
        decision = enrich_intent_decision(
            classify_chat_intent("Explain TLS in HGSC tumor microenvironment"),
            "Explain TLS in HGSC tumor microenvironment",
        )
        route = resolve_expert_model(decision, "Explain TLS in HGSC tumor microenvironment", agent_category="cancer_oncology")
        self.assertIsNotNone(route)
        self.assertEqual(route.layer, "expert")
        self.assertIn("med", route.model)

    @patch.dict(os.environ, {"OMEIA_EXPERT_ROUTING_ENABLED": "true"}, clear=False)
    def test_spatial_category_routes_spatial_model(self) -> None:
        decision = enrich_intent_decision(
            classify_chat_intent("Compare Visium and GeoMx for TME"),
            "Compare Visium and GeoMx for TME",
        )
        route = resolve_expert_model(decision, "Compare Visium and GeoMx for TME", agent_category="spatial_multiplex")
        self.assertIsNotNone(route)
        self.assertEqual(route.reason, "spatial_expert")

    @patch.dict(os.environ, {"OMEIA_EXPERT_ROUTING_ENABLED": "false"}, clear=False)
    def test_disabled_returns_none(self) -> None:
        decision = enrich_intent_decision(classify_chat_intent("TLS in ovarian cancer"), "TLS in ovarian cancer")
        self.assertIsNone(resolve_expert_model(decision, "TLS in ovarian cancer"))


if __name__ == "__main__":
    unittest.main()
