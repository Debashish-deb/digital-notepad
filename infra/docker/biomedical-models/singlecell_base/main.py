"""Base single-cell model service — Geneformer, scGPT, scPRINT share this pattern."""
from __future__ import annotations

import os
import sys
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, "/app/shared")
from fastapi_base import ModelHolder  # noqa: E402

SERVICE_NAME = os.getenv("SINGLECELL_SERVICE_NAME", "singlecell")
HF_MODEL_ID = os.getenv("SINGLECELL_HF_ID", "ctheodoris/Geneformer")
MODEL_KEY = os.getenv("SINGLECELL_MODEL_KEY", "geneformer")

app = FastAPI(title=f"OMEIA {SERVICE_NAME}", version="1.0.0")
MODEL = ModelHolder(HF_MODEL_ID, kind="single-cell")


class SingleCellEmbedRequest(BaseModel):
    """Generic gene-list payload — specialized loaders can extend later."""
    genes: list[str] = Field(default_factory=list, max_length=5000)
    values: list[float] = Field(default_factory=list, max_length=5000)
    text: str = Field("", max_length=4000)


class SingleCellEmbedResponse(BaseModel):
    model: str
    vector: list[float]
    note: str


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": SERVICE_NAME, "model": MODEL.status}


@app.get("/info")
def info() -> dict[str, Any]:
    return {
        "service": SERVICE_NAME,
        "hf_id": HF_MODEL_ID,
        "model_key": MODEL_KEY,
        "input_schema": "genes+values or text fallback",
    }


@app.post("/embed", response_model=SingleCellEmbedResponse)
def embed(body: SingleCellEmbedRequest) -> SingleCellEmbedResponse:
    """Fallback: mean-pool gene tokens via underlying HF encoder until native loader wired."""
    if body.text:
        payload = body.text
    elif body.genes:
        pairs = list(zip(body.genes[:200], body.values[:200])) if body.values else body.genes[:200]
        payload = " ".join(str(p) for p in pairs)
    else:
        raise HTTPException(status_code=400, detail="Provide text or genes")
    try:
        vec = MODEL.embed_texts([payload], max_length=512)[0]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return SingleCellEmbedResponse(
        model=MODEL_KEY,
        vector=vec,
        note="Generic HF fallback embedding — replace with native Geneformer/scGPT/scPRINT forward pass when wired.",
    )
