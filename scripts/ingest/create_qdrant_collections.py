#!/usr/bin/env python3
from __future__ import annotations
import os
from pathlib import Path
import yaml
from qdrant_client import QdrantClient
from qdrant_client.http import models

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "qdrant_collections.yaml"

def distance(name: str) -> models.Distance:
    name = name.lower()
    if name == "cosine":
        return models.Distance.COSINE
    if name in {"dot", "dotproduct"}:
        return models.Distance.DOT
    if name in {"euclidean", "l2"}:
        return models.Distance.EUCLID
    raise ValueError(f"Unsupported distance: {name}")

def main() -> None:
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY") or None
    client = QdrantClient(url=qdrant_url, api_key=api_key)
    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    existing = [c.name for c in client.get_collections().collections]
    for name, spec in cfg["collections"].items():
        vector_specs = {}
        for vector_name, vector_cfg in spec["vectors"].items():
            vector_specs[vector_name] = models.VectorParams(
                size=int(vector_cfg["size"]),
                distance=distance(vector_cfg["distance"]),
            )
        if name not in existing:
            client.create_collection(collection_name=name, vectors_config=vector_specs)
            print(f"created collection: {name}")
        else:
            print(f"collection already exists: {name}")
        for field in spec.get("payload_indexes", []):
            try:
                client.create_payload_index(
                    collection_name=name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                print(f"  indexed payload: {field}")
            except Exception as exc:
                print(f"  payload index skipped for {field}: {exc}")

if __name__ == "__main__":
    main()
