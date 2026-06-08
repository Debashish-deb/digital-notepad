"""OMEIA document metadata engine — enrichment without physical file changes."""
from app_skeleton.api.metadata_engine.enricher import enrich_inventory_row, enrich_all
from app_skeleton.api.metadata_engine.scoring import metadata_score, metadata_grade

__all__ = ["enrich_inventory_row", "enrich_all", "metadata_score", "metadata_grade"]
