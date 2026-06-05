#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import math
import os
import re
from typing import List
from qdrant_client import QdrantClient

def pseudo_semantic_embed(text: str, dim: int = 384) -> List[float]:
    vec = [0.0] * dim
    words = re.findall(r'[a-zA-Z0-9_\-]+', text.lower())
    for w in words:
        if w in {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
                 'to', 'in', 'of', 'for', 'on', 'with', 'at', 'by', 'from', 'this',
                 'that', 'these', 'those', 'it', 'its', 'as'}:
            continue
        h = int(hashlib.sha256(w.encode('utf-8')).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v*v for v in vec))
    if norm < 0.0001:
        h_all = hashlib.sha256(text.encode('utf-8')).digest()
        vec = [((h_all[i % len(h_all)] / 255.0) * 2 - 1) for i in range(dim)]
        norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v / norm for v in vec]

def main() -> None:
    client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
    question = "What is the SPACE project about?"
    res = client.query_points(collection_name="doc_chunks", query=pseudo_semantic_embed(question), using="text", limit=3)
    hits = res.points
    print(f"Question: {question}\n")
    for hit in hits:
        print(f"score={hit.score:.4f} title={hit.payload.get('title')}")
        print(hit.payload.get("text_preview"))
        print("-" * 80)

if __name__ == "__main__":
    main()

