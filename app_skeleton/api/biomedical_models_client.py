"""Client for Docker-hosted biomedical model FastAPI services."""
from __future__ import annotations

import logging
import os
from typing import Any

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

LOGGER = logging.getLogger(__name__)


def _url(name: str, default: str) -> str:
    return os.getenv(name, default).rstrip("/")


class BiomedicalModelsClient:
    def __init__(self) -> None:
        self.gateway_url = _url("BIOMEDICAL_MODELS_GATEWAY_URL", "http://127.0.0.1:8100")
        self.embeddings_url = _url("BIOMEDICAL_EMBEDDINGS_URL", "http://127.0.0.1:8101")
        self.biogpt_url = _url("BIOMEDICAL_BIOGPT_URL", "http://127.0.0.1:8102")
        self.txgemma_url = _url("BIOMEDICAL_TXGEMMA_URL", "http://127.0.0.1:8103")
        self.timeout = float(os.getenv("BIOMEDICAL_MODELS_TIMEOUT_SEC", "120"))

    def available(self) -> bool:
        return httpx is not None

    def catalog(self) -> dict[str, Any]:
        return self._get(f"{self.gateway_url}/catalog")

    def status(self) -> dict[str, Any]:
        return self._get(f"{self.gateway_url}/status")

    def embed(
        self,
        texts: list[str],
        *,
        model: str = "medcpt-query",
        max_length: int = 512,
    ) -> dict[str, Any]:
        return self._post(
            f"{self.embeddings_url}/embed",
            {"texts": texts, "model": model, "max_length": max_length},
        )

    def generate_biogpt(self, prompt: str, *, max_new_tokens: int = 256) -> dict[str, Any]:
        return self._post(
            f"{self.biogpt_url}/generate",
            {"prompt": prompt, "max_new_tokens": max_new_tokens},
        )

    def generate_txgemma(self, prompt: str, *, max_new_tokens: int = 512) -> dict[str, Any]:
        return self._post(
            f"{self.txgemma_url}/generate",
            {"prompt": prompt, "max_new_tokens": max_new_tokens},
        )

    def _get(self, url: str) -> dict[str, Any]:
        if not httpx:
            return {"error": "httpx_not_installed"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.get(url)
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            LOGGER.warning("biomedical models GET %s failed: %s", url, exc)
            return {"error": str(exc)}

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not httpx:
            return {"error": "httpx_not_installed"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            LOGGER.warning("biomedical models POST %s failed: %s", url, exc)
            return {"error": str(exc)}


_client: BiomedicalModelsClient | None = None


def get_biomedical_models_client() -> BiomedicalModelsClient:
    global _client
    if _client is None:
        _client = BiomedicalModelsClient()
    return _client
