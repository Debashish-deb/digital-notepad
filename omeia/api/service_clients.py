"""Lazy factories for Qdrant, LLM, and RAG agents — warmed in app lifespan."""
from __future__ import annotations

import logging
import os
from typing import Any

from qdrant_client import QdrantClient

from omeia.api.agents import RAGAgent
from omeia.api.llm_client import LLMClient

LOGGER = logging.getLogger(__name__)


class _ServiceHolder:
    qdrant: QdrantClient | None = None
    llm: LLMClient | None = None
    rag: RAGAgent | None = None

    @classmethod
    def ensure(cls) -> None:
        if cls.qdrant is not None:
            return
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        cls.qdrant = QdrantClient(url=url)
        cls.llm = LLMClient()
        cls.rag = RAGAgent(cls.qdrant, cls.llm)
        LOGGER.debug("Service clients initialized (qdrant, llm, rag)")


class _LazyProxy:
    __slots__ = ("_attr",)

    def __init__(self, attr: str) -> None:
        self._attr = attr

    def _resolve(self) -> Any:
        _ServiceHolder.ensure()
        return getattr(_ServiceHolder, self._attr)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._resolve()(*args, **kwargs)

    def __bool__(self) -> bool:
        return True


qdrant_client: QdrantClient | _LazyProxy = _LazyProxy("qdrant")
llm_client: LLMClient | _LazyProxy = _LazyProxy("llm")
rag_agent: RAGAgent | _LazyProxy = _LazyProxy("rag")


def warm_clients() -> None:
    """Eagerly warm clients during lifespan startup."""
    _ServiceHolder.ensure()


def init_service_clients() -> None:
    warm_clients()


def get_qdrant_client() -> QdrantClient:
    _ServiceHolder.ensure()
    assert _ServiceHolder.qdrant is not None
    return _ServiceHolder.qdrant


def get_llm_client() -> LLMClient:
    _ServiceHolder.ensure()
    assert _ServiceHolder.llm is not None
    return _ServiceHolder.llm
