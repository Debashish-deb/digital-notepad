"""Knowledge graph entity/edge CRUD in Postgres (no Neo4j)."""
from __future__ import annotations

import logging
from typing import Any

from omeia.api.entity_relation_extractor import (
    extract_entities_rule_based,
    extract_relations_rule_based,
    normalize_name,
)
from omeia.api.learning_models import KnowledgeEntityType, StorageStatus
from omeia.api.learning_store import insert_graph_edge, list_graph_edges

LOGGER = logging.getLogger(__name__)

_ENTITY_TYPE_MAP = {
    "disease": KnowledgeEntityType.CANCER_TYPE.value,
    "biomarker": KnowledgeEntityType.MARKER.value,
    "technology": KnowledgeEntityType.METHOD.value,
    "software_tool": KnowledgeEntityType.METHOD.value,
    "immune_structure": KnowledgeEntityType.CELL_TYPE.value,
    "concept": KnowledgeEntityType.OUTCOME.value,
}


def map_entity_type(raw_type: str) -> str:
    return _ENTITY_TYPE_MAP.get(raw_type, KnowledgeEntityType.OUTCOME.value)


def extract_graph_from_text(
    text: str,
    *,
    knowledge_id: str | None = None,
    storage_status: str = StorageStatus.DRAFT.value,
    confidence_score: float = 0.0,
) -> list[dict[str, Any]]:
    """Build graph edges from rule-based entity/relation extraction."""
    entities = extract_entities_rule_based(text)
    relations = extract_relations_rule_based(text, entities)
    edges: list[dict[str, Any]] = []

    for rel in relations:
        subject_type = map_entity_type(
            next((e["entity_type"] for e in entities if e["name"] == rel["subject"]), "concept")
        )
        edge_id = insert_graph_edge(
            knowledge_id=knowledge_id,
            subject_name=rel["subject"],
            subject_type=subject_type,
            relation_type=rel["relation_type"],
            object_name=rel["object"],
            object_type=KnowledgeEntityType.OUTCOME.value,
            confidence_score=confidence_score or float(rel.get("confidence", 0.5) * 100),
            evidence_text=rel.get("evidence_text"),
            storage_status=storage_status,
            metadata={"normalized_subject": normalize_name(rel["subject"])},
        )
        if edge_id:
            edges.append({
                "edge_id": edge_id,
                "subject_name": rel["subject"],
                "subject_type": subject_type,
                "relation_type": rel["relation_type"],
                "object_name": rel["object"],
                "object_type": KnowledgeEntityType.OUTCOME.value,
                "confidence_score": confidence_score,
                "storage_status": storage_status,
            })

    for ent in entities:
        if ent["name"] in {e["subject_name"] for e in edges}:
            continue
        edge_id = insert_graph_edge(
            knowledge_id=knowledge_id,
            subject_name=ent["name"],
            subject_type=map_entity_type(ent.get("entity_type", "concept")),
            relation_type="MENTIONED_IN",
            object_name="lab_knowledge",
            object_type=KnowledgeEntityType.RESEARCH_PROJECT.value,
            confidence_score=confidence_score or float(ent.get("confidence", 0.5) * 100),
            evidence_text=(text or "")[:400],
            storage_status=storage_status,
            metadata={"aliases": ent.get("aliases", [])},
        )
        if edge_id:
            edges.append({
                "edge_id": edge_id,
                "subject_name": ent["name"],
                "subject_type": map_entity_type(ent.get("entity_type", "concept")),
                "relation_type": "MENTIONED_IN",
                "object_name": "lab_knowledge",
                "object_type": KnowledgeEntityType.RESEARCH_PROJECT.value,
                "confidence_score": confidence_score,
                "storage_status": storage_status,
            })

    return edges


def query_graph(
    *,
    subject_name: str | None = None,
    object_name: str | None = None,
    include_draft: bool = True,
    limit: int = 50,
) -> list[dict[str, Any]]:
    statuses = [StorageStatus.VERIFIED.value]
    if include_draft:
        statuses.extend([StorageStatus.DRAFT.value, StorageStatus.LOW_CONFIDENCE.value])
    return list_graph_edges(
        subject_name=subject_name,
        object_name=object_name,
        status_filter=statuses,
        limit=limit,
    )
