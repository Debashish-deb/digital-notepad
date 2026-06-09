"""Bridge imaging channel markers to research knowledge base entities."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

# Canonical multiplex markers used in scientific instrument presets.
IMAGING_MARKERS: dict[str, dict[str, Any]] = {
    "DAPI": {"entity_type": "marker", "role": "nuclear", "panel": "common"},
    "CD3": {"entity_type": "marker", "role": "T_cell", "panel": "immune"},
    "CD4": {"entity_type": "marker", "role": "T_helper", "panel": "immune"},
    "CD8": {"entity_type": "marker", "role": "cytotoxic_T", "panel": "immune"},
    "CD20": {"entity_type": "marker", "role": "B_cell", "panel": "immune"},
    "CD68": {"entity_type": "marker", "role": "macrophage", "panel": "myeloid"},
    "CD163": {"entity_type": "marker", "role": "M2_macrophage", "panel": "myeloid"},
    "TIM3": {"entity_type": "marker", "role": "exhaustion", "panel": "exhaustion"},
    "NKG2A": {"entity_type": "marker", "role": "NK_inhibitory", "panel": "exhaustion"},
    "Ki67": {"entity_type": "marker", "role": "proliferation", "panel": "tumor"},
    "PanCK": {"entity_type": "marker", "role": "epithelial", "panel": "tumor"},
    "HLA-DPB1": {"entity_type": "marker", "role": "MHC_II", "panel": "tumor_microenvironment"},
}

CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs" / "research_knowledge"


def _load_kb_marker_aliases() -> dict[str, str]:
    """Optional JSON alias map: imaging label -> KB entity name."""
    path = CONFIG_DIR / "imaging_marker_aliases.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in (data.get("aliases") or {}).items()}
    except Exception as exc:
        LOGGER.debug("imaging marker aliases load failed: %s", exc)
        return {}


def _search_kb_entity(marker_name: str) -> dict[str, Any] | None:
    """Best-effort lookup in Postgres research entities."""
    try:
        import psycopg

        from omeia.api.supabase_config import postgres_conn

        with psycopg.connect(postgres_conn(), connect_timeout=4) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT entity_id::text, entity_type, canonical_name, aliases
                    FROM platform.research_entity
                    WHERE lower(canonical_name) = lower(%s)
                       OR %s = ANY(SELECT jsonb_array_elements_text(COALESCE(aliases, '[]'::jsonb)))
                    LIMIT 1;
                    """,
                    (marker_name, marker_name),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "entity_id": row[0],
                        "entity_type": row[1],
                        "canonical_name": row[2],
                        "aliases": row[3] or [],
                        "source": "postgres",
                    }
    except Exception as exc:
        LOGGER.debug("KB entity lookup failed for %s: %s", marker_name, exc)
    return None


def build_marker_graph(channel_names: list[str] | None = None) -> dict[str, Any]:
    """Return marker nodes and KB links for imaging channel labels."""
    aliases = _load_kb_marker_aliases()
    names = channel_names or list(IMAGING_MARKERS.keys())
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for label in names:
        key = label.strip()
        if not key:
            continue
        meta = IMAGING_MARKERS.get(key, {"entity_type": "marker", "role": "unknown", "panel": "custom"})
        kb_name = aliases.get(key, key)
        kb_entity = _search_kb_entity(kb_name)
        node = {
            "id": key,
            "label": key,
            "imaging_role": meta.get("role"),
            "panel": meta.get("panel"),
            "kb_linked": kb_entity is not None,
        }
        if kb_entity:
            node["kb_entity_id"] = kb_entity["entity_id"]
            node["kb_canonical_name"] = kb_entity["canonical_name"]
            edges.append(
                {
                    "from": key,
                    "to": kb_entity["canonical_name"],
                    "relation": "maps_to_kb_entity",
                    "entity_id": kb_entity["entity_id"],
                }
            )
        nodes.append(node)

    return {
        "nodes": nodes,
        "edges": edges,
        "marker_count": len(nodes),
        "kb_linked_count": sum(1 for n in nodes if n.get("kb_linked")),
    }
