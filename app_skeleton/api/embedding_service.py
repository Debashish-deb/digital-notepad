"""Unified text embeddings — Ollama SOTA with hashed offline fallback."""
from __future__ import annotations

import logging
import math
import os
import re
from typing import TYPE_CHECKING

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

if TYPE_CHECKING:
    from app_skeleton.api.llm_client import LLMClient

LOGGER = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_+.-]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "to", "in",
    "of", "for", "on", "with", "at", "by", "from", "this", "that", "these", "those",
}


def embedding_dim() -> int:
    return max(32, min(int(os.getenv("TEXT_EMBEDDING_DIM", "384") or 384), 4096))


def _ollama_embed_available() -> bool:
    if requests is None:
        return False
    try:
        base = _ollama_base()
        headers: dict[str, str] = {}
        token = (os.getenv("OLLAMA_INTERNAL_TOKEN") or os.getenv("OLLAMA_PROXY_TOKEN") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = requests.get(f"{base}/api/tags", headers=headers, timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def embedding_provider() -> str:
    raw = (os.getenv("EMBEDDING_PROVIDER", "auto") or "auto").strip().lower()
    if raw == "auto":
        return "ollama" if _ollama_embed_available() else "hash"
    return raw


def embedding_model_name() -> str:
    return (os.getenv("TEXT_EMBEDDING_MODEL", "nomic-embed-text") or "nomic-embed-text").strip()


def _ollama_base() -> str:
    base = (os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434") or "").strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return base


def _normalize(vec: list[float], dim: int) -> list[float]:
    if len(vec) > dim:
        vec = vec[:dim]
    elif len(vec) < dim:
        vec = vec + [0.0] * (dim - len(vec))
    norm = math.sqrt(sum(v * v for v in vec))
    if norm < 1e-9:
        return [0.0] * dim
    return [v / norm for v in vec]


def hash_embed(text: str, *, dim: int | None = None) -> list[float]:
    """Deterministic L2-normalized hash embedding (offline fallback)."""
    import hashlib

    dim = dim or embedding_dim()
    vec = [0.0] * dim
    tokens = _TOKEN_RE.findall((text or "").lower())
    for token in tokens:
        if token in _STOPWORDS:
            continue
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + min(len(token), 24) / 24.0
        vec[idx] += sign * weight
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def ollama_embed(text: str, *, model: str | None = None, dim: int | None = None) -> list[float]:
    """Call Ollama /api/embeddings (pull model first: ollama pull nomic-embed-text)."""
    if requests is None:
        raise RuntimeError("requests package unavailable")
    model = model or embedding_model_name()
    dim = dim or embedding_dim()
    url = f"{_ollama_base()}/api/embeddings"
    headers: dict[str, str] = {}
    token = (os.getenv("OLLAMA_INTERNAL_TOKEN") or os.getenv("OLLAMA_PROXY_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.post(
        url,
        json={"model": model, "prompt": (text or "")[:8000]},
        headers=headers,
        timeout=float(os.getenv("OLLAMA_EMBED_TIMEOUT_SEC", "60")),
    )
    resp.raise_for_status()
    data = resp.json()
    vector = data.get("embedding") or []
    if not vector:
        raise ValueError("Ollama returned empty embedding")
    return _normalize([float(x) for x in vector], dim)


def embed_text(text: str, *, llm: LLMClient | None = None) -> list[float]:
    """Primary embed entry — Ollama when configured, else hash."""
    dim = embedding_dim()
    if embedding_provider() == "ollama":
        try:
            return ollama_embed(text, dim=dim)
        except Exception as exc:
            LOGGER.warning("Ollama embed failed (%s); using hash fallback", exc)
    if llm is not None and hasattr(llm, "_hash_embed"):
        return llm._hash_embed(text, dim=dim)
    return hash_embed(text, dim=dim)


def embed_many(texts: list[str], *, llm: LLMClient | None = None) -> list[list[float]]:
    return [embed_text(t, llm=llm) for t in texts]
