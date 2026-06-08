"""BioGPT text-generation FastAPI service."""
from __future__ import annotations

import sys
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, "/app/shared")
from fastapi_base import ModelHolder  # noqa: E402

app = FastAPI(title="OMEIA BioGPT", version="1.0.0")
MODEL = ModelHolder("microsoft/biogpt", kind="text-generation")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    max_new_tokens: int = Field(256, ge=16, le=1024)


class GenerateResponse(BaseModel):
    model: str = "biogpt"
    text: str


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "biogpt", "model": MODEL.status}


@app.post("/generate", response_model=GenerateResponse)
def generate(body: GenerateRequest) -> GenerateResponse:
    try:
        text = MODEL.generate(body.prompt, max_new_tokens=body.max_new_tokens)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GenerateResponse(text=text)
