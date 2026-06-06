"""Biomedical models gateway — catalog + health aggregation."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI

app = FastAPI(title="OMEIA Biomedical Models Gateway", version="1.0.0")

REGISTRY_PATH = Path("/app/shared/model_registry.json")
SERVICES = {
    "embeddings": os.getenv("BIOMED_EMBEDDINGS_URL", "http://biomedical-embeddings:8101"),
    "biogpt": os.getenv("BIOMED_BIOGPT_URL", "http://biomedical-biogpt:8102"),
    "txgemma": os.getenv("BIOMED_TXGEMMA_URL", "http://biomedical-txgemma:8103"),
    "geneformer": os.getenv("BIOMED_GENEFORMER_URL", "http://biomedical-geneformer:8110"),
    "scgpt": os.getenv("BIOMED_SCGPT_URL", "http://biomedical-scgpt:8111"),
    "scprint": os.getenv("BIOMED_SCPRINT_URL", "http://biomedical-scprint:8112"),
}


def _registry() -> dict[str, Any]:
    if REGISTRY_PATH.is_file():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {"version": 1, "services": {}}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "biomedical-gateway"}


@app.get("/catalog")
def catalog() -> dict[str, Any]:
    reg = _registry()
    return {
        "skipped": reg.get("skip_already_dockerized", []),
        "services": reg.get("services", {}),
    }


@app.get("/status")
async def status() -> dict[str, Any]:
    out: dict[str, Any] = {"gateway": "ok", "services": {}}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, base in SERVICES.items():
            try:
                r = await client.get(f"{base.rstrip('/')}/health")
                out["services"][name] = {"url": base, "healthy": r.status_code == 200, "body": r.json()}
            except Exception as exc:
                out["services"][name] = {"url": base, "healthy": False, "error": str(exc)[:200]}
    return out
