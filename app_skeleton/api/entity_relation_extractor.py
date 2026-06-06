from __future__ import annotations

import re
from typing import Any

DOMAIN_ENTITIES = {
    "HGSC": ["HGSC", "HGSOC", "high-grade serous ovarian cancer", "high-grade serous ovarian carcinoma"],
    "MHC class II": ["MHC class II", "MHCII", "HLA-DP", "HLA-DQ", "HLA-DR"],
    "TLS": ["tertiary lymphoid structure", "tertiary lymphoid structures", "TLS", "lymphoid aggregate"],
    "tCyCIF": ["tCyCIF", "CyCIF", "cyclic immunofluorescence"],
    "Visium": ["Visium", "spatial transcriptomics", "10x Genomics Visium"],
    "GeoMx": ["GeoMx", "digital spatial profiling"],
    "scRNA-seq": ["scRNA-seq", "single-cell RNA-seq", "single cell RNA sequencing"],
    "Ashlar": ["Ashlar", "stitching", "registration"],
    "BaSiC": ["BaSiC", "illumination correction", "flat-field", "dark-field"],
    "Mesmer": ["Mesmer", "DeepCell", "whole-cell segmentation"],
    "StarDist": ["StarDist", "nuclei segmentation"],
}

ENTITY_TYPES = {
    "HGSC": "disease",
    "MHC class II": "biomarker",
    "TLS": "immune_structure",
    "tCyCIF": "technology",
    "Visium": "technology",
    "GeoMx": "technology",
    "scRNA-seq": "technology",
    "Ashlar": "software_tool",
    "BaSiC": "software_tool",
    "Mesmer": "software_tool",
    "StarDist": "software_tool",
}


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")


def extract_entities_rule_based(text: str) -> list[dict[str, Any]]:
    lower = (text or "").lower()
    entities = []
    for canonical, aliases in DOMAIN_ENTITIES.items():
        for alias in aliases:
            if alias.lower() in lower:
                entities.append({
                    "name": canonical,
                    "normalized_name": normalize_name(canonical),
                    "entity_type": ENTITY_TYPES.get(canonical, "concept"),
                    "aliases": aliases,
                    "confidence": 0.75,
                })
                break
    return entities


def extract_relations_rule_based(text: str, entities: list[dict[str, Any]], source_id: str | None = None) -> list[dict[str, Any]]:
    names = {e["name"] for e in entities}
    relations = []
    evidence = (text or "")[:700]
    if "MHC class II" in names and "HGSC" in names:
        relations.append({
            "subject": "MHC class II",
            "relation_type": "ASSOCIATED_WITH",
            "object": "HGSC spatial immune ecosystems",
            "evidence_text": evidence,
            "source_id": source_id,
            "confidence": 0.65,
        })
    if "TLS" in names and "HGSC" in names:
        relations.append({
            "subject": "TLS",
            "relation_type": "OCCURS_IN",
            "object": "HGSC tumor microenvironment",
            "evidence_text": evidence,
            "source_id": source_id,
            "confidence": 0.65,
        })
    if "tCyCIF" in names:
        relations.append({
            "subject": "tCyCIF",
            "relation_type": "MEASURES",
            "object": "spatial protein expression",
            "evidence_text": evidence,
            "source_id": source_id,
            "confidence": 0.6,
        })
    return relations
