"""PubMedBERT, BioBERT, MedCPT embedding FastAPI service."""
from __future__ import annotations

import os
import sys
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, "/app/shared")
from fastapi_base import ModelHolder  # noqa: E402

app = FastAPI(title="OMEIA Biomedical Embeddings", version="1.0.0")

MODELS: dict[str, ModelHolder] = {
    "pubmedbert": ModelHolder("microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"),
    "biobert": ModelHolder("dmis-lab/biobert-v1.1"),
    "medcpt-query": ModelHolder("ncbi/MedCPT-Query-Encoder"),
    "medcpt-article": ModelHolder("ncbi/MedCPT-Article-Encoder"),
}

ModelName = Literal["pubmedbert", "biobert", "medcpt-query", "medcpt-article"]


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=32)
    model: ModelName = "medcpt-query"
    max_length: int = Field(512, ge=32, le=512)


class EmbedResponse(BaseModel):
    model: str
    dimension: int
    vectors: list[list[float]]


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "biomedical-embeddings", "models": {k: v.status for k, v in MODELS.items()}}


@app.get("/models")
def list_models() -> dict[str, Any]:
    return {"models": list(MODELS.keys())}


@app.post("/embed", response_model=EmbedResponse)
def embed(body: EmbedRequest) -> EmbedResponse:
    holder = MODELS.get(body.model)
    if not holder:
        raise HTTPException(status_code=400, detail="Unknown model")
    try:
        vectors = holder.embed_texts(body.texts, max_length=body.max_length)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    dim = len(vectors[0]) if vectors else 0
    return EmbedResponse(model=body.model, dimension=dim, vectors=vectors)


@app.on_event("startup")
def preload() -> None:
    if os.getenv("BIOMODEL_PRELOAD", "").lower() in ("1", "true", "yes"):
        for name in os.getenv("BIOMODEL_PRELOAD_MODELS", "medcpt-query").split(","):
            name = name.strip()
            if name in MODELS:
                MODELS[name].ensure_loaded()
