"""Proxy routes to Docker biomedical model services."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from omeia.api.biomedical_models_client import get_biomedical_models_client
from omeia.security.auth import require_platform_user

router = APIRouter(tags=["biomedical-models"])


class EmbedBody(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=16)
    model: str = "medcpt-query"
    max_length: int = Field(512, ge=32, le=512)


class GenerateBody(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=12000)
    max_new_tokens: int = Field(256, ge=16, le=2048)


@router.get("/api/biomedical-models/catalog")
def catalog(user: dict[str, Any] = Depends(require_platform_user)) -> dict[str, Any]:
    return get_biomedical_models_client().catalog()


@router.get("/api/biomedical-models/status")
def status(user: dict[str, Any] = Depends(require_platform_user)) -> dict[str, Any]:
    return get_biomedical_models_client().status()


@router.post("/api/biomedical-models/embed")
def embed(body: EmbedBody, user: dict[str, Any] = Depends(require_platform_user)) -> dict[str, Any]:
    result = get_biomedical_models_client().embed(body.texts, model=body.model, max_length=body.max_length)
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.post("/api/biomedical-models/generate/biogpt")
def generate_biogpt(body: GenerateBody, user: dict[str, Any] = Depends(require_platform_user)) -> dict[str, Any]:
    result = get_biomedical_models_client().generate_biogpt(body.prompt, max_new_tokens=body.max_new_tokens)
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.post("/api/biomedical-models/generate/txgemma")
def generate_txgemma(body: GenerateBody, user: dict[str, Any] = Depends(require_platform_user)) -> dict[str, Any]:
    result = get_biomedical_models_client().generate_txgemma(body.prompt, max_new_tokens=body.max_new_tokens)
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])
    return result
