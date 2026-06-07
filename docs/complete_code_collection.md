# OMEIA Digital Notepad - Complete Code Collection

**Generated:** June 6, 2026  
**Purpose:** Complete source code collection organized by architecture  
**Repository:** digital-notepad (Farkki-AI Platform)

---

## Table of Contents

1. [Backend API (Python)](#1-backend-api-python)
   - 1.1 Main Application
   - 1.2 API Routers
   - 1.3 Core Services
   - 1.4 Database Processing
   - 1.5 Security & Authentication
2. [Frontend React (JSX/JS/CSS)](#2-frontend-react-jsxjscss)
   - 2.1 Main Application
   - 2.2 Screens
   - 2.3 Components
   - 2.4 API Client
   - 2.5 Utils & Helpers
3. [Scripts (Python)](#3-scripts-python)
   - 3.1 Database Ingestion
   - 3.2 Vector Database Setup
   - 3.3 Document Processing
4. [Configuration](#4-configuration)
   - 4.1 Docker Compose
   - 4.2 YAML Configs
5. [Database Schema](#5-database-schema)
   - 5.1 Core Schema
   - 5.2 Feature Schema
   - 5.3 Platform Schema

---

# 1. Backend API (Python)

## 1.1 Main Application

### File: `app_skeleton/api/main.py`

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app_skeleton.security.environment import validate_environment
from app_skeleton.security.cors import get_cors_origins
from app_skeleton.security.auth import require_platform_user

# Validate security environment immediately
validate_environment()

from app_skeleton.api.common import *
from app_skeleton.api.common import _app_lifespan
from app_skeleton.api.routers import health, research, copilot, knowledge, vault, storage, datapad, digitalization, search
from app_skeleton.security import secure_files

app = FastAPI(title="OMEIA Research Copilot API", version="0.4.0-premium", lifespan=_app_lifespan)

_cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)

# Public static mounts (dev previews — spreadsheet/PDF fetches use /database-static/)
if CSC_MEDIA_DIR.exists():
    app.mount("/csc-media", StaticFiles(directory=str(CSC_MEDIA_DIR)), name="csc-media")

if PROJECTS_ROOT.exists():
    app.mount("/projects-static", StaticFiles(directory=str(PROJECTS_ROOT)), name="projects-static")

if DATABASE_ROOT.exists():
    app.mount("/database-static", StaticFiles(directory=str(DATABASE_ROOT)), name="database-static")

# All standard API routes must require authentication
api_dependencies = [Depends(require_platform_user)]

app.include_router(research.router, dependencies=api_dependencies)
app.include_router(copilot.router, dependencies=api_dependencies)
app.include_router(knowledge.router, dependencies=api_dependencies)
app.include_router(vault.router, dependencies=api_dependencies)
app.include_router(storage.router, dependencies=api_dependencies)
app.include_router(datapad.router, dependencies=api_dependencies)
app.include_router(digitalization.router, dependencies=api_dependencies)
app.include_router(search.router, dependencies=api_dependencies)

# Secure files router has its own internal dependency checks, 
# but we can enforce it here as well for defense-in-depth, though it's already in the router definition
app.include_router(secure_files.router)
```

## 1.2 API Routers

### File: `app_skeleton/api/routers/copilot.py`

```python
from app_skeleton.security.permissions import require_role
from app_skeleton.security.auth import require_platform_user
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from app_skeleton.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

@router.get("/api/billing-instructions")
def get_billing_instructions() -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT document_id,
                           document_type,
                           source_language,
                           author_name,
                           author_email,
                           subject,
                           raw_text,
                           structured_json
                    FROM core.documents 
                    WHERE document_type IN (
                        'billing_instruction', 
                        'order_form', 
                        'shipping_customs_statement', 
                        'shipping_instruction', 
                        'courier_service_account_instruction', 
                        'courier_service_instruction'
                    ) 
                    ORDER BY created_at DESC;
                """)
                rows = cur.fetchall()
                documents = []
                for row in rows:
                    if not row or not row[7]:
                        continue
                    structured_json = row[7] if isinstance(row[7], dict) else {}
                    document = {
                        "document_id": str(row[0]),
                        "document_type": row[1],
                        "source_language": row[2],
                        "author_name": row[3],
                        "author_email": row[4],
                        "subject": row[5],
                        "raw_text": row[6],
                        **structured_json,
                    }
                    documents.append(document)
                return {"documents": documents}
    except Exception as exc:
        LOGGER.warning("Failed to fetch billing instructions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/ask", response_model=QuestionResponse)
def ask(req: QuestionRequest, user: dict = Depends(require_platform_user)) -> QuestionResponse:
    mode = (req.mode or "documentation_only").strip().lower()
    if mode != "search_only":
        require_role(user, ["editor", "admin"])
    # 1. Initialize temporary LLM client dynamically if configured from frontend
    active_llm = llm_client
    if req.llm_provider and req.llm_provider != "mock":
        active_llm = LLMClient()
        active_llm.provider = req.llm_provider.lower()
        active_llm.model = req.llm_model or active_llm.model
        active_llm.api_key = req.llm_api_key or active_llm.api_key
        active_llm.base_url = req.llm_base_url or active_llm.base_url
        active_llm._init_client()

    # 2. Run privacy audit checks
    audit = PrivacyGuardrailAgent.audit_query(req.question)
    limitations = []
    
    if not audit["is_safe"]:
        limitations.append(f"Safety Alert: Potential Patient Identifiers Redacted ({', '.join(audit['violations'])}).")
        # Block forwarding query to external LLM provider if set to public
        if active_llm.provider != "ollama" and active_llm.provider != "mock":
            return QuestionResponse(
                answer="Error: User query blocked by local privacy guardrails because patient-identifiable data (PII) was detected and LLM is configured to utilize external cloud APIs. De-identify patient data and try again.",
                limitations=limitations,
                sources=[],
                database_counts={},
                is_safe=False
            )

    safe_question = audit["redacted_text"]

    if mode == "search_only":
        from app_skeleton.api.search_service import SearchService

        search_svc = SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=llm_client)
        codes = ",".join(req.project_codes) if req.project_codes else None
        unified = search_svc.unified_search(
            safe_question,
            project_codes=codes,
            mode="hybrid",
            limit=20,
            user_role=user.get("role"),
            user_email=user.get("email"),
        )
        sources = [
            SourceInfo(
                title=h.title,
                source_type=h.source_type or h.bucket,
                source_uuid=h.document_code or h.relative_path or h.id,
                chunk_id=h.id,
                text_preview=h.snippet,
                score=h.score,
                nav=h.nav.model_dump() if h.nav else None,
                bucket=h.bucket,
            )
            for h in unified.hits
        ]
        return QuestionResponse(
            answer="",
            limitations=["Search-only mode — retrieval without LLM synthesis. Use clickable sources to open documents."],
            sources=sources,
            database_counts={},
            is_safe=True,
            search_hits=[h.model_dump() for h in unified.hits],
        )

    # 3. Fetch structured stats from Postgres
    db_data = query_postgres_metadata(req.project_codes)

    clinical_block = _clinical_context_for_question(safe_question, req.project_codes or [])
    
    # 4. Retrieve via shared SearchService + project-scoped RAGAgent
    from app_skeleton.api.search_service import SearchService

    search_svc = SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=active_llm)
    unified_hits = search_svc.hits_for_copilot(
        safe_question, project_codes=req.project_codes, limit=12
    )

    temp_rag = RAGAgent(qdrant_client, active_llm)
    rag_sources = temp_rag.retrieve(safe_question, req.project_codes)

    seen_ids = {h.id for h in unified_hits}
    retrieved_sources: list[dict] = []
    for hit in unified_hits:
        retrieved_sources.append({
            "title": hit.title,
            "source_type": hit.source_type or hit.bucket,
            "source_uuid": hit.document_code or hit.relative_path or hit.id,
            "chunk_id": hit.id,
            "text_preview": hit.snippet,
            "score": hit.score,
            "nav": hit.nav.model_dump() if hit.nav else None,
            "bucket": hit.bucket,
        })

    for src in rag_sources:
        cid = src.get("chunk_id")
        if cid and cid in seen_ids:
            continue
        if cid:
            seen_ids.add(cid)
        retrieved_sources.append({
            "title": src["title"],
            "source_type": src["source_type"],
            "source_uuid": src["source_uuid"],
            "chunk_id": cid,
            "text_preview": src["text_preview"],
            "score": src.get("score", 0.0),
            "nav": None,
            "bucket": "lab",
        })
    retrieved_sources = retrieved_sources[:12]

    sources = [
        SourceInfo(
            title=src["title"],
            source_type=src["source_type"],
            source_uuid=src["source_uuid"],
            chunk_id=src["chunk_id"],
            text_preview=src["text_preview"],
            score=src["score"],
            nav=src.get("nav"),
            bucket=src.get("bucket"),
        ) for src in retrieved_sources
    ]
    search_hits_payload = [h.model_dump() for h in unified_hits[:12]]

    # 5. Build prompt and generate response using active_llm
    context_str = ""
    for i, src in enumerate(sources):
        context_str += f"[{i+1}] Source: {src.title} (Type: {src.source_type})\n{src.text_preview}\n\n"
        
    system_prompt = (
        "You are the OMEIA Clinical-Spatial Biology Copilot, an expert AI platform assistant.\n"
        "Your task is to answer the researcher's query based on the database counts and documentation snippets.\n"
        "Follow these rules:\n"
        "1. Report patient/sample statistics exactly as provided in the database counts. Do NOT invent/hallucinate figures.\n"
        "2. If code installation commands or scripts are requested, return structured code blocks detailing required parameters.\n"
        "3. Cite references [1], [2], etc., corresponding to context blocks.\n"
        "4. Remain precise, professional, and highlight limitations."
    )
    
    user_content = (
        f"Database counts:\n"
        f"- Patient total: {db_data.get('patient_count', 0)}\n"
        f"- Sample total: {db_data.get('sample_count', 0)}\n"
        f"- Projects: {db_data.get('project_samples', {})}\n"
        f"- Modalities: {db_data.get('modality_samples', {})}\n\n"
        f"{('Structured clinical/feature analysis:\\n' + clinical_block + '\\n\\n') if clinical_block else ''}"
        f"Documentation Context:\n"
        f"{context_str}\n"
        f"Question: {safe_question}"
    )

    answer = active_llm.generate(user_content, system_prompt)

    if active_llm.provider == "mock":
        limitations.append("Running in local mock-synthesis mode because no LLM_API_KEY is configured.")

    # Audit conversations to DB
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Add default user conversation log
                cur.execute(
                    "INSERT INTO platform.conversation (title, project_code) VALUES (%s, %s) RETURNING conversation_id;",
                    ("Research Query Conversation", req.project_codes[0] if req.project_codes else "ALL")
                )
                conv_id = cur.fetchone()[0]
                
                # Insert messages
                cur.execute(
                    "INSERT INTO platform.message (conversation_id, role, content) VALUES (%s, 'user', %s);",
                    (conv_id, safe_question)
                )
                cur.execute(
                    "INSERT INTO platform.message (conversation_id, role, content, retrieved_chunks) VALUES (%s, 'assistant', %s, %s);",
                    (conv_id, answer, psycopg.types.json.Jsonb([s.model_dump() for s in sources]))
                )
    except Exception as exc:
        LOGGER.warning("Failed to log message to Postgres database: %s", exc)

    return QuestionResponse(
        answer=answer,
        limitations=limitations,
        sources=sources,
        database_counts=db_data,
        is_safe=True,
        search_hits=search_hits_payload,
    )
```

### File: `app_skeleton/api/routers/datapad.py`

```python
from app_skeleton.security.permissions import require_role
from app_skeleton.security.auth import require_platform_user
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from app_skeleton.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg
from app_skeleton.api.thumbnail_service import generate_thumbnail

router = APIRouter()

@router.get("/api/project-files/list/{project_code}")
def list_project_files(project_code: str):
    folder_path = get_project_folder_path(project_code)
    if not folder_path:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    files = scan_project_text_files(folder_path)
    return files

@router.get("/api/project-files/preview-text")
def project_file_preview_text(
    project_code: str = Query(...),
    relative_path: str = Query(...),
) -> dict:
    """Text preview for project files (chunks, document index, or live extraction)."""
    try:
        return get_project_file_preview_text(project_code, relative_path, max_chars=MAX_PROJECT_FILE_READ_BYTES)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/api/projects/{project_code}/digital-twin")
def project_digital_twin(project_code: str, refresh: bool = False) -> dict:
    try:
        return get_digital_twin(project_code, refresh=refresh)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.put("/api/projects/{project_code}/digital-twin")
def save_project_digital_twin(project_code: str, body: dict, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        return update_digital_twin(project_code, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

## 1.3 Core Services

### File: `app_skeleton/api/llm_client.py`

```python
"""Provider-routed LLM client for OMEIA.

Production-grade drop-in upgrade for the original LLMClient.

Compatibility promises:
- Keeps LLMClient.generate(prompt, system_prompt), healthCheck(), and embed().
- Keeps public attributes provider/model/api_key/base_url for existing router code.
- Uses deterministic local embeddings by default so local RAG still works offline.

Safety / quality upgrades:
- Optional OpenAI SDK import so tests/tools do not crash if the dependency is absent.
- Bounded provider fallback without recursive state corruption.
- Provider-specific env resolution with no secret logging.
- OpenAI-compatible providers: OpenAI, Groq, OpenRouter, Together, DeepSeek, Ollama.
- Robust mock synthesis for offline demos and CI.
"""
from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from dataclasses import dataclass
from typing import Any, List

try:
    import requests
except Exception:
    requests = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

LOGGER = logging.getLogger(__name__)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "to", "in",
    "of", "for", "on", "with", "at", "by", "from", "this", "that", "these", "those",
    "it", "its", "as", "be", "can", "how", "what", "why", "when", "where", "which",
    "there", "their", "they", "we", "you", "your", "our", "about", "into", "over",
}
_TOKEN_RE = re.compile(r"[a-zA-Z0-9_+.-]+")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bounded_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    return max(low, min(parsed, high))


def _bounded_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(low, min(parsed, high))


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""
    extra_headers: dict[str, str] | None = None

    @property
    def is_mock(self) -> bool:
        return self.provider == "mock"

    @property
    def is_local(self) -> bool:
        return self.provider in {"mock", "ollama"}


class LLMClient:
    """Small OpenAI-compatible provider router used by the API."""

    _KNOWN_PROVIDERS = {"mock", "openai", "groq", "openrouter", "together", "ollama", "deepseek"}

    def __init__(self):
        self.provider = _env("LLM_PROVIDER", "mock").lower() or "mock"
        if self.provider not in self._KNOWN_PROVIDERS:
            LOGGER.warning("Unknown LLM_PROVIDER=%s; falling back to mock", self.provider)
            self.provider = "mock"

        self.model = _env("LLM_MODEL", "mock-model") or "mock-model"
        self.api_key = _env("LLM_API_KEY", "")
        self.base_url = _env("LLM_BASE_URL", "")
        fallback_env = _env("LLM_FALLBACK_PROVIDERS", "groq,openai,openrouter,together,deepseek,ollama,mock")
        self.fallback_providers = self._normalize_provider_list(fallback_env)
        if "mock" not in self.fallback_providers:
            self.fallback_providers.append("mock")

        self.timeout_seconds = _bounded_float(_env("LLM_TIMEOUT_SECONDS", "45"), 45.0, 2.0, 240.0)
        self.max_tokens = _bounded_int(_env("LLM_MAX_TOKENS", "1400"), 1400, 64, 12000)
        self.temperature = _bounded_float(_env("LLM_TEMPERATURE", "0.0"), 0.0, 0.0, 2.0)
        self.client: Any | None = None
        self.last_provider_errors: list[str] = []
        self._init_client()

    @classmethod
    def _normalize_provider_list(cls, value: str) -> list[str]:
        providers: list[str] = []
        for raw in (value or "").split(","):
            provider = raw.strip().lower()
            if provider and provider in cls._KNOWN_PROVIDERS and provider not in providers:
                providers.append(provider)
        return providers or ["mock"]

    def _config_for(self, provider: str) -> ProviderConfig:
        provider = (provider or "mock").lower()
        if provider == "openai":
            return ProviderConfig(
                "openai",
                _env("OPENAI_MODEL", self.model if self.provider == "openai" else "gpt-4o-mini"),
                _env("OPENAI_API_KEY", self.api_key if self.provider == "openai" else ""),
                _env("OPENAI_BASE_URL", ""),
            )
        if provider == "groq":
            return ProviderConfig(
                "groq",
                _env("GROQ_MODEL", "llama-3.1-70b-versatile"),
                _env("GROQ_API_KEY", self.api_key if self.provider == "groq" else ""),
                _env("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            )
        if provider == "ollama":
            return ProviderConfig(
                "ollama",
                _env("OLLAMA_MODEL", self.model if self.provider == "ollama" else "llama3"),
                "ollama",
                _env("OLLAMA_BASE_URL", self.base_url or "http://localhost:11434/v1"),
            )
        return ProviderConfig("mock", "mock-model", "", "")

    def _current_config(self) -> ProviderConfig:
        if self.provider == "mock":
            return ProviderConfig("mock", "mock-model", "", "")
        if self.provider == "ollama":
            return ProviderConfig("ollama", self.model or "llama3", "ollama", self.base_url or "http://localhost:11434/v1")
        return ProviderConfig(self.provider, self.model, self.api_key, self.base_url)

    def _init_client(self) -> None:
        """Initialise the configured primary provider, falling back to mock if unavailable."""
        cfg = self._current_config()
        if cfg.provider != "mock" and not (cfg.api_key or cfg.provider == "ollama"):
            cfg = self._config_for(cfg.provider)

        if cfg.provider == "mock" or (not cfg.api_key and cfg.provider != "ollama") or OpenAI is None:
            if cfg.provider != "mock" and OpenAI is None:
                LOGGER.warning("OpenAI SDK is unavailable; LLM provider %s disabled", cfg.provider)
            self.provider, self.model, self.api_key, self.base_url = "mock", "mock-model", "", ""
            self.client = None
            return

        self.provider, self.model, self.api_key, self.base_url = cfg.provider, cfg.model, cfg.api_key, cfg.base_url
        self.client = self._client_for(cfg)

    def _client_for(self, cfg: ProviderConfig) -> Any | None:
        if OpenAI is None:
            return None
        if cfg.provider == "mock" or (not cfg.api_key and cfg.provider != "ollama"):
            return None
        kwargs: dict[str, Any] = {
            "api_key": cfg.api_key,
            "timeout": self.timeout_seconds,
            "max_retries": 1,
        }
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        if cfg.extra_headers:
            kwargs["default_headers"] = cfg.extra_headers
        return OpenAI(**kwargs)

    def healthCheck(self) -> bool:
        """Verify whether the current provider is responsive."""
        if self.provider == "mock":
            return True
        try:
            if self.provider == "ollama":
                if requests is None:
                    return False
                base = (self.base_url or "http://localhost:11434/v1").replace("/v1", "")
                return requests.get(base, timeout=2).status_code < 500
            if self.client:
                self.client.models.list()
                return True
        except Exception as exc:
            LOGGER.debug("LLM health check failed for %s: %s", self.provider, exc)
        return False

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate conversational text with automatic fallback routing."""
        primary = self.provider or "mock"
        providers = [primary] + [p for p in self.fallback_providers if p != primary]
        errors: list[str] = []

        for provider in providers:
            cfg = self._current_config() if provider == primary else self._config_for(provider)
            if cfg.provider != "mock" and not cfg.api_key and cfg.provider != "ollama":
                continue
            if cfg.provider != "mock" and OpenAI is None:
                errors.append(f"{cfg.provider}: OpenAISDKMissing")
                continue

            try:
                result = self._chat_once(cfg, prompt, system_prompt)
                if result:
                    self.provider, self.model, self.api_key, self.base_url = cfg.provider, cfg.model, cfg.api_key, cfg.base_url
                    self.client = self._client_for(cfg)
                    self.last_provider_errors = errors
                    return result
            except Exception as exc:
                errors.append(f"{cfg.provider}: {type(exc).__name__}")
                LOGGER.warning("LLM provider %s failed: %s", cfg.provider, exc)

        self.last_provider_errors = errors
        fallback = self._mock_generate(prompt, system_prompt)
        if errors:
            fallback += "\n\n*Provider fallback note: " + "; ".join(errors[:4]) + ".*"
        return fallback

    def embed(self, text: str, dim: int = 384) -> List[float]:
        """Generate a stable L2-normalized hashed embedding for offline RAG."""
        dim = _bounded_int(dim, 384, 32, 4096)
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

            if len(token) >= 5:
                for i in range(min(len(token) - 2, 10)):
                    gram = token[i:i + 3]
                    gd = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
                    vec[int.from_bytes(gd[:4], "big") % dim] += 0.22

        norm = math.sqrt(sum(v * v for v in vec))
        if norm < 1e-9:
            seed = hashlib.blake2b((text or "empty").encode("utf-8"), digest_size=32).digest()
            vec = [((seed[i % len(seed)] / 255.0) * 2.0 - 1.0) for i in range(dim)]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
```

### File: `app_skeleton/api/qdrant_vectors.py`

```python
"""Portable Qdrant vector helpers — named vector ``text`` for doc_chunks everywhere."""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

LOGGER = logging.getLogger(__name__)

DOC_CHUNKS_COLLECTION = os.getenv("DOCUMENT_QDRANT_COLLECTION", "doc_chunks")
TEXT_VECTOR_NAME = os.getenv("DOCUMENT_QDRANT_VECTOR_NAME", "text")
EMBEDDING_DIM = int(os.getenv("TEXT_EMBEDDING_DIM", "384"))


def qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "http://localhost:6333").strip()


def qdrant_api_key() -> str | None:
    key = os.getenv("QDRANT_API_KEY", "").strip()
    return key or None


def get_qdrant_client(url: str | None = None) -> QdrantClient:
    return QdrantClient(url=url or qdrant_url(), api_key=qdrant_api_key())


def ping_qdrant(client: QdrantClient | None = None) -> bool:
    try:
        c = client or get_qdrant_client()
        c.get_collections()
        return True
    except Exception as exc:
        LOGGER.debug("Qdrant ping failed: %s", exc)
        return False


def ensure_named_text_collection(
    client: QdrantClient,
    collection: str | None = None,
) -> None:
    """Create collection with named vector ``text`` if missing (portable default)."""
    collection = collection or DOC_CHUNKS_COLLECTION
    try:
        client.get_collection(collection)
        return
    except Exception:
        pass
    client.create_collection(
        collection_name=collection,
        vectors_config={
            TEXT_VECTOR_NAME: models.VectorParams(
                size=EMBEDDING_DIM,
                distance=models.Distance.COSINE,
            ),
        },
    )
    LOGGER.info("Created Qdrant collection %s (vector=%s)", collection, TEXT_VECTOR_NAME)


def stable_point_uuid(seed: str) -> str:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return str(uuid.UUID(hex=digest))


def upsert_text_points(
    client: QdrantClient,
    points: list[models.PointStruct],
    *,
    collection: str | None = None,
) -> int:
    """Upsert points using named vector ``text``. Returns count upserted."""
    if not points:
        return 0
    collection = collection or DOC_CHUNKS_COLLECTION
    ensure_named_text_collection(client, collection)
    normalized: list[models.PointStruct] = []
    for pt in points:
        vec = pt.vector
        if isinstance(vec, list):
            vec = {TEXT_VECTOR_NAME: vec}
        elif isinstance(vec, dict) and TEXT_VECTOR_NAME not in vec and len(vec) == 1:
            vec = {TEXT_VECTOR_NAME: next(iter(vec.values()))}
        normalized.append(
            models.PointStruct(id=pt.id, vector=vec, payload=pt.payload or {})
        )
    client.upsert(collection_name=collection, points=normalized)
    return len(normalized)
```

## 1.4 Database Processing

### File: `app_skeleton/api/database_processor.py`

```python
"""Extract, chunk, and persist lab database sections (Overview, Orders, Social, Wet-lab)."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app_skeleton.api import document_extraction as de
from app_skeleton.api.database_sections import DATABASE_SECTIONS, section_root
from app_skeleton.api.paths import DATABASE_ROOT, PROCESSED_DIR, PUBLIC_PROCESSED_DIR
from app_skeleton.api.project_processor import sync_public_processed


def _iter_chunks_from_disk(section_id: str) -> list[dict[str, Any]]:
    """Load all chunks from jsonl (complete) with JSON fallback."""
    chunks: list[dict[str, Any]] = []
    jsonl_path = processed_chunks_path(section_id)
    if jsonl_path.exists():
        try:
            with jsonl_path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    chunks.append(json.loads(line))
            return chunks
        except Exception:
            pass
    twin = load_processed_section(section_id)
    return list(twin.get("vector_chunks") or []) if twin else []


def write_lab_manifest() -> Path:
    """Small index for the UI to discover processed lab sections without API."""
    PUBLIC_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": list_processed_summary(),
    }
    out = PUBLIC_PROCESSED_DIR / "lab__manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out

LAB_STORAGE_PREFIX = "lab__"


def storage_key(section_id: str) -> str:
    return f"{LAB_STORAGE_PREFIX}{section_id}"


def processed_json_path(section_id: str) -> Path:
    return PROCESSED_DIR / f"{storage_key(section_id)}.json"


def processed_chunks_path(section_id: str) -> Path:
    return PROCESSED_DIR / f"{storage_key(section_id)}.chunks.jsonl"


def _annotate_chunks(chunks: list[dict[str, Any]], section_id: str, section_label: str) -> list[dict[str, Any]]:
    out = []
    for chunk in chunks:
        row = dict(chunk)
        row["section_id"] = section_id
        row["section_label"] = section_label
        row["scope"] = "lab"
        row["project_code"] = None
        out.append(row)
    return out


def process_section(section_id: str) -> dict[str, Any]:
    if section_id not in DATABASE_SECTIONS:
        raise ValueError(f"Unknown database section: {section_id}")
    meta = DATABASE_SECTIONS[section_id]
    root = section_root(section_id)
    if not root.is_dir():
        raise FileNotFoundError(f"Section folder not found: {root}")

    file_inventory = de._scan_folder(root)
    all_assets = de._scan_all_assets(root)
    content_library = de._build_content_library(all_assets) if all_assets else {
        "sections": [], "figures_gallery": [], "totals": {}, "figure_count": 0,
    }

    document_records: list[de.ExtractionResult] = []
    vector_chunks: list[dict[str, Any]] = []
    extraction_summary: dict[str, Any] = {
        "total_scannable_assets": 0,
        "extracted_records": 0,
        "chunk_count": 0,
        "status_counts": {},
        "extractor_counts": {},
        "extension_counts": {},
        "errors": [],
    }
    if all_assets:
        document_records, vector_chunks, extraction_summary = de._extract_project_documents(root, all_assets)

    vector_chunks = _annotate_chunks(vector_chunks, section_id, meta["label"])
    combined_text = de._combine_text_records(document_records)
    document_index = [
        r.as_json(include_text=False, include_chunks=False)
        for r in document_records[: de.DEFAULT_MAX_DOCS_IN_JSON]
    ]

    extracted_count = extraction_summary.get("status_counts", {}).get("extracted", 0)
    return {
        "section_id": section_id,
        "storage_key": storage_key(section_id),
        "scope": "lab",
        "section_label": meta["label"],
        "description": meta["description"],
        "relative_root": meta["relative_root"],
        "database_root": str(DATABASE_ROOT),
        "content_root": str(root),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "source_files_count": len(file_inventory),
        "total_assets_count": len(all_assets),
        "content_library": content_library,
        "document_index": document_index,
        "vector_chunks": vector_chunks[: de.DEFAULT_MAX_CHUNKS_IN_JSON],
        "extraction": extraction_summary,
        "folder_tree": _folder_tree_from_assets(all_assets)[:500],
        "combined_text_chars": len(combined_text),
        "metrics": {
            "document_count": len(file_inventory),
            "total_assets": len(all_assets),
            "scannable_assets": extraction_summary.get("total_scannable_assets", 0),
            "extracted_document_count": extracted_count,
            "knowledge_chunk_count": len(vector_chunks),
            "extraction_error_count": len(extraction_summary.get("errors", [])),
            "figure_count": content_library.get("figure_count", 0),
        },
    }


def save_processed_section(section_id: str, data: dict[str, Any] | None = None) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    payload = data or process_section(section_id)
    out = processed_json_path(section_id)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    chunks = payload.get("vector_chunks") or []
    chunks_out = processed_chunks_path(section_id)
    with chunks_out.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    sync_public_processed()
    write_lab_manifest()
    return out


def load_processed_section(section_id: str) -> dict[str, Any] | None:
    path = processed_json_path(section_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_section_record(section_id: str, *, refresh: bool = False) -> dict[str, Any]:
    if not refresh:
        cached = load_processed_section(section_id)
        if cached:
            return cached
    data = process_section(section_id)
    save_processed_section(section_id, data)
    return data
```

---

# 2. Frontend React (JSX/JS/CSS)

## 2.1 Main Application

### File: `app_skeleton/ui/react_frontend/src/main.jsx`

```jsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './fonts.css';   /* Source Sans 3, Source Serif 4, JetBrains Mono */
import './index.css';
import './typography.css';
import './theme/themeManager.css';
import './theme/consistency.css';

import { ApiProvider } from './api/ApiContext.jsx';
import { LocaleProvider } from './contexts/LocaleContext.jsx';
import { ThemeProvider } from './contexts/ThemeContext.jsx';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Farkki Lab Assistant could not start because #root was not found.');
}

createRoot(rootElement).render(
  <StrictMode>
    <ApiProvider>
      <LocaleProvider>
        <ThemeProvider>
          <App />
        </ThemeProvider>
      </LocaleProvider>
    </ApiProvider>
  </StrictMode>,
);
```

### File: `app_skeleton/ui/react_frontend/src/App.jsx`

```jsx
import React, { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ModuleShell from './components/ModuleShell';
import ErrorBoundary from './components/ErrorBoundary';
import DashboardScreen from './screens/DashboardScreen';
import GlobalSearchOverlay from './components/GlobalSearchOverlay';
import ProjectsScreen from './screens/ProjectsScreen';
import NotebookWikiScreen from './screens/NotebookWikiScreen';
import DecisionsScreen from './screens/DecisionsScreen';
import TasksScreen from './screens/TasksScreen';
import BioinformaticsHubScreen from './screens/BioinformaticsHubScreen';
import AiLabAssistantScreen from './screens/AiLabAssistantScreen';
import FeatureClinicalScreen from './screens/FeatureClinicalScreen';
import LabKnowledgeScreen from './screens/LabKnowledgeScreen';
const DataStorageScreen = lazy(() => import('./screens/DataStorageScreen'));
import AdministrationScreen from './screens/AdministrationScreen';
import IngestionDashboard from './screens/IngestionDashboard';
import DigitalizationDashboard from './screens/DigitalizationDashboard';
import KnowledgeSearchScreen from './screens/KnowledgeSearchScreen';
import LabCorpusBrowser from './components/LabCorpusBrowser.jsx';
import { getApiUrl, apiFetch } from './api/client.js';
import { useApiContext } from './api/ApiContext.jsx';
import CycifScreen from './screens/CycifScreen';
import { TaskpadProvider } from './contexts/TaskpadContext.jsx';
import TaskpadSheet from './components/TaskpadSheet.jsx';
import { CENTRAL_WORKER_ID, TASKPAD_SCOPES } from './utils/taskpadRegistry.js';

import {
  OrdersTasksPanel,
  OrdersRegisterPanel,
  OrdersRelatedPanel,
  OrdersBillingPanel,
  OrdersArchivePanel,
} from './screens/OrdersHubScreen';
import OverviewDocumentsScreen from './screens/OverviewDocumentsScreen.jsx';
import SectionDocumentsScreen from './screens/SectionDocumentsScreen.jsx';
import { getSectionDocumentsConfig } from './utils/sectionDocumentsConfig.js';
import {
  WetLabProtocolsPanel,
  WetLabTasksPanel,
  WetLabInventoryPanel,
} from './screens/WetLabScreen';
import { projectsCatalog } from './data/projectsCatalog.js';
import { teamDirectory } from './data/teamDirectory.js';
import { activityLogs } from './data/activityLogs.js';
import { platformStats } from './data/platformStats.js';
import { mergeProjectRecord } from './utils/projectUtils.js';
import {
  COMPUTATIONAL_LEGACY_NESTED,
  findMainNav,
  findSubNav,
  parseNavFromStorage,
} from './config/navigation';
import { useGuiT } from './i18n/useGuiT.js';
import { initFirebaseAnalytics } from './config/firebase.js';
import LoginScreen from './screens/LoginScreen.jsx';
import { stashOmniboxPrefill } from './utils/searchHits.js';
import './App.css';

const DEFAULT_PROJECT_CODES = Object.freeze(['SPACE', 'EyeMT', 'KRAS']);
const DEFAULT_STATS = Object.freeze({
  patient_count: 0,
  sample_count: 0,
  project_samples: {},
});

const NAV_STORAGE_KEY = 'farkki_nav_v2';

const API_URL = getApiUrl();

function safeStorageGet(key, fallback) {
  try {
    return window.localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function safeStorageSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // ignore
  }
}

function resolveComputationalNav(raw) {
  if (raw.main === 'computational' && raw.sub === 'utilities' && raw.hubNested === 'tools') {
    return { main: raw.main, sub: 'tools', hubNested: null };
  }
  const legacy = COMPUTATIONAL_LEGACY_NESTED[raw.sub];
  if (raw.main === 'computational' && legacy) {
    return { main: raw.main, sub: legacy.tab, hubNested: legacy.section };
  }
  if (raw.main === 'computational' && raw.sub === 'tools') {
    return { main: raw.main, sub: 'tools', hubNested: null };
  }
  return { main: raw.main, sub: raw.sub, hubNested: null };
}

function migrateLegacyNav(stored) {
  const legacy = parseNavFromStorage(stored);
  if (legacy) {
    if (
      legacy.main === 'overview' &&
      (legacy.sub === 'dashboard' || legacy.sub === 'research')
    ) {
      return { main: 'overview', sub: 'get_started' };
    }
    return legacy;
  }
  const map = {
    dashboard: { main: 'overview', sub: 'get_started' },
    projects: { main: 'projects_data', sub: 'portfolio' },
    notebook: { main: 'projects_data', sub: 'notebook' },
    chat: { main: 'ai_assistant', sub: 'copilot' },
    decisions: { main: 'projects_data', sub: 'decisions' },
    tasks: { main: 'projects_data', sub: 'portfolio' },
    bioinformatics: { main: 'computational', sub: 'onboarding' },
    features: { main: 'projects_data', sub: 'features' },
    ai_assistant: { main: 'ai_assistant', sub: 'prompts' },
  };
  return map[stored] || { main: 'overview', sub: 'get_started' };
}

function normalizeProjectCodes(value) {
  const list = Array.isArray(value) ? value : DEFAULT_PROJECT_CODES;
  const seen = new Set();
  return list
    .map((code) => String(code || '').trim())
    .filter(Boolean)
    .filter((code) => {
      const key = code.toUpperCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

async function fetchJson(path, { signal, timeoutMs = 12_000, params } = {}) {
  return apiFetch(path, { signal, timeoutMs, params });
}

function mergeProjectsWithCatalog(remoteProjects = []) {
  const remote = Array.isArray(remoteProjects) ? remoteProjects : [];
  const merged = remote.map((project) => mergeProjectRecord(project));
  const seen = new Set(merged.map((project) => project.project_code));
  for (const catalogProject of projectsCatalog) {
    if (!seen.has(catalogProject.project_code)) {
      merged.push(mergeProjectRecord(catalogProject));
    }
  }
  return merged.sort((a, b) => (a.project_index || 999) - (b.project_index || 999));
}

function App() {
  const {
    API_URL: contextApiUrl,
    authReady,
    isAuthenticated,
    authDisabled,
    firebaseAuthEnabled,
    onAuthToken,
    authUser,
    userProfile,
    signOut,
  } = useApiContext();
  const { t, nav } = useGuiT();
  const resolvedApiUrl = contextApiUrl || API_URL;
  const initialResolved = resolveComputationalNav(migrateLegacyNav(safeStorageGet(NAV_STORAGE_KEY, '')));
  const [navMain, setNavMain] = useState(initialResolved.main);
  const [navSub, setNavSub] = useState(initialResolved.sub);
  const [sidebarExpandedMain, setSidebarExpandedMain] = useState(null);
  const [hubNestedSection, setHubNestedSection] = useState(initialResolved.hubNested);
  const [selectedProject, setSelectedProject] = useState(null);
  const [dbProjects, setDbProjects] = useState(() => mergeProjectsWithCatalog(projectsCatalog));
  const [projectCodes, setProjectCodesState] = useState(DEFAULT_PROJECT_CODES);
  const [stats, setStats] = useState(platformStats || DEFAULT_STATS);
  const [team, setTeam] = useState(teamDirectory || []);
  const [auditLogs, setAuditLogs] = useState(activityLogs || []);
  const [loadState, setLoadState] = useState({ phase: 'idle' });
  const [apiHealth, setApiHealth] = useState(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const handleOpenSearch = useCallback((query) => {
    if (query?.trim()) stashOmniboxPrefill(query);
    setIsSearchOpen(true);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const activeTitle = nav.sectionTitle(navMain, navSub);
  const isLoading = loadState.phase === 'loading' || loadState.phase === 'refreshing';
  const subNav = findSubNav(navMain, navSub);
  const localizedSub = nav.findSub(navMain, navSub);
  const loadMessage = useMemo(() => {
    if (loadState.phase === 'loading' || loadState.phase === 'refreshing') {
      return t('common.syncing');
    }
    if (loadState.phase === 'ready') return t('common.projectsSynced');
    if (loadState.phase === 'warning') return t('common.syncWarning');
    return t('common.ready');
  }, [loadState.phase, t]);

  const setProjectCodes = useCallback((nextValue) => {
    setProjectCodesState((previous) => {
      const resolved = typeof nextValue === 'function' ? nextValue(previous) : nextValue;
      const normalized = normalizeProjectCodes(resolved);
      return normalized.length ? normalized : [...DEFAULT_PROJECT_CODES];
    });
  }, []);

  const resetProject = useCallback(() => setSelectedProject(null), []);

  const handleNavChange = useCallback((main, sub) => {
    const mainItem = findMainNav(main);
    let subId = sub || mainItem.defaultSub;
    let nested = null;
    if (mainItem.id === 'computational') {
      const legacy = COMPUTATIONAL_LEGACY_NESTED[subId];
      if (legacy) {
        nested = legacy.section;
        subId = legacy.tab;
      }
    }
    setNavMain(mainItem.id);
    setNavSub(subId);
    setHubNestedSection(nested);
    setSidebarExpandedMain(mainItem.id);
    if (!mainItem.keepsProject) setSelectedProject(null);
  }, []);

  const handleMainNavClick = useCallback((main) => {
    const mainItem = findMainNav(main);
    if (main === navMain && sidebarExpandedMain === main) {
      setSidebarExpandedMain(null);
      return;
    }
    if (main === navMain) {
      setSidebarExpandedMain(main);
      return;
    }
    handleNavChange(main, mainItem.defaultSub);
  }, [navMain, sidebarExpandedMain, handleNavChange]);

  const commonProps = useMemo(() => ({ dbProjects, API_URL: resolvedApiUrl }), [dbProjects, resolvedApiUrl]);

  const fetchProjects = useCallback(async (signal) => {
    const data = await fetchJson('/projects', { signal, timeoutMs: 14_000 });
    if (Array.isArray(data) && data.length > 0) {
      setDbProjects(mergeProjectsWithCatalog(data));
    } else {
      setDbProjects(mergeProjectsWithCatalog(projectsCatalog));
    }
  }, []);

  const refreshReferenceData = useCallback(async (signal, phase = 'refreshing') => {
    setLoadState({ phase });
    try {
      await fetchProjects(signal);
      setLoadState({ phase: 'ready' });
    } catch (err) {
      setLoadState({ phase: 'warning' });
    }
  }, [fetchProjects]);

  const renderScreenBody = () => {
    const screen = subNav.screen;

    switch (screen) {
      case 'dashboard':
        return (
          <DashboardScreen
            stats={stats}
            team={team}
            auditLogs={auditLogs}
            projectCodes={projectCodes}
            setProjectCodes={setProjectCodes}
            dbProjects={dbProjects}
            API_URL={resolvedApiUrl}
            hideHeader
            onNavigate={handleNavChange}
          />
        );
      case 'orders_billing':
        return <OrdersBillingPanel API_URL={resolvedApiUrl} />;
      case 'orders_archive':
        return <OrdersArchivePanel />;
      case 'orders_register':
        return <OrdersRegisterPanel />;
      case 'orders_related':
        return <OrdersRelatedPanel auditLogs={auditLogs} />;
      case 'projects':
        return (
          <ProjectsScreen
            dbProjects={dbProjects}
            selectedProject={selectedProject}
            setSelectedProject={setSelectedProject}
            fetchProjects={() => refreshReferenceData(new AbortController().signal)}
            API_URL={API_URL}
          />
        );
      case 'notebook':
        return <NotebookWikiScreen {...commonProps} hideHeader />;
      case 'decisions':
        return <DecisionsScreen {...commonProps} hideHeader />;
      case 'features':
        return <FeatureClinicalScreen {...commonProps} hideHeader />;
      case 'bioinformatics':
        return (
          <BioinformaticsHubScreen
            key={`bio-${navSub}-${hubNestedSection || 'root'}`}
            {...commonProps}
            activeSubTab={subNav.bioSub || navSub}
            hubNestedSection={hubNestedSection}
            hideChrome
            onNavigate={handleNavChange}
          />
        );
      case 'chat':
        return (
          <AiLabAssistantScreen
            {...commonProps}
            activeSubTab="copilot"
            hideChrome
            onNavigate={handleNavChange}
            onSelectProject={(code) => setSelectedProject(code)}
            onOpenSearch={handleOpenSearch}
          />
        );
      case 'ai_assistant':
        return (
          <AiLabAssistantScreen
            {...commonProps}
            activeSubTab={subNav.aiSub || navSub}
            hideChrome
            onNavigate={handleNavChange}
            onSelectProject={(code) => setSelectedProject(code)}
            onOpenSearch={handleOpenSearch}
          />
        );
      default:
        return null;
    }
  };

  const handleManualRefresh = useCallback(() => {
    refreshReferenceData(new AbortController().signal, 'refreshing');
  }, [refreshReferenceData]);

  useEffect(() => {
    initFirebaseAnalytics();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch('/health', { signal: controller.signal, timeoutMs: 8_000 })
      .then((data) => {
        if (data?.status === 'ok') {
          setApiHealth(data);
        } else {
          setApiHealth({ status: 'unreachable', database_connected: false });
        }
      })
      .catch(() => setApiHealth({ status: 'unreachable', database_connected: false }));
    return () => controller.abort();
  }, [resolvedApiUrl]);

  useEffect(() => {
    document.title = `${activeTitle} · ${t('common.documentTitleSuffix')}`;
  }, [activeTitle, t]);

  useEffect(() => {
    safeStorageSet(NAV_STORAGE_KEY, `${navMain}:${navSub}`);
  }, [navMain, navSub]);

  useEffect(() => {
    const controller = new AbortController();
    refreshReferenceData(controller.signal, 'loading');
    return () => controller.abort();
  }, [refreshReferenceData]);

  const requireLogin = firebaseAuthEnabled && !authDisabled;

  if (firebaseAuthEnabled && !authReady) {
    return (
      <div className="auth-boot-screen" role="status" aria-live="polite">
        <p>{t('common.syncing')}</p>
      </div>
    );
  }

  if (requireLogin && authReady && !isAuthenticated) {
    return <LoginScreen onAuthenticated={onAuthToken} />;
  }

  const displayUser =
    userProfile?.name ||
    authUser?.displayName ||
    (authUser?.email ? authUser.email.split('@')[0] : null) ||
    'Guest';

  const useModuleShell = navMain !== 'projects_data' || navSub !== 'portfolio' || !selectedProject;
  const useWideContentShell = navMain === 'data_storage' && navSub === 'documents';

  const activeScreen = useModuleShell ? (
    <ModuleShell
      mainId={navMain}
      subId={navSub}
      onSubChange={(sub) => handleNavChange(navMain, sub)}
      onRefresh={handleManualRefresh}
      isRefreshing={isLoading}
      compact={navMain === 'computational'}
      landing
    >
      {renderScreenBody()}
    </ModuleShell>
  ) : (
    renderScreenBody()
  );

  return (
    <TaskpadProvider>
      <div className="app-container" data-loading={isLoading ? 'true' : 'false'}>
        <a className="skip-link" href="#main-content">
          {t('common.skipToWorkspace')}
        </a>

      <Sidebar
        navMain={navMain}
        navSub={navSub}
        sidebarExpandedMain={sidebarExpandedMain}
        onNavChange={handleNavChange}
        onMainNavClick={handleMainNavClick}
        onResetProject={resetProject}
        apiHealth={apiHealth}
        apiUrl={resolvedApiUrl}
        onOpenSearch={() => setIsSearchOpen(true)}
        userLabel={displayUser}
        userEmail={authUser?.email || userProfile?.email}
        onSignOut={requireLogin ? signOut : null}
      />

      <main
        id="main-content"
        className="main-content"
        tabIndex={-1}
        aria-busy={isLoading}
        aria-labelledby="app-current-section"
      >
        <div className={`app-content-shell${useWideContentShell ? ' app-content-shell--wide' : ''}`}>
          <span className="sr-only" id="app-current-section" role="status" aria-live="polite">
            {activeTitle} — {loadMessage}
          </span>
          {!useModuleShell ? (
            <button
              type="button"
              className="app-refresh-fab"
              onClick={handleManualRefresh}
              disabled={isLoading}
              aria-label={isLoading ? t('common.syncing') : t('common.refreshAria')}
              title={isLoading ? t('common.syncing') : t('common.refresh')}
            >
              <RefreshCw size={15} className={isLoading ? 'spin' : undefined} aria-hidden />
            </button>
          ) : null}

          <ErrorBoundary>{activeScreen}</ErrorBoundary>
        </div>
      </main>

        <GlobalSearchOverlay
          isOpen={isSearchOpen}
          onClose={() => setIsSearchOpen(false)}
          onNavigate={handleNavChange}
          onSelectProject={(code) => setSelectedProject(code)}
          onAskAi={(q) => {
            handleNavChange('ai_assistant', 'copilot');
            try {
              sessionStorage.setItem('farkki_search_last_query', q);
            } catch {
              /* ignore */
            }
          }}
          projectCode={
            typeof selectedProject === 'string'
              ? selectedProject
              : selectedProject?.project_code || selectedProject?.code
          }
        />

        <div className="app-central-taskpad-host" aria-live="polite">
          <TaskpadSheet scope={TASKPAD_SCOPES.CENTRAL} workerId={CENTRAL_WORKER_ID} />
        </div>
      </div>
    </TaskpadProvider>
  );
}

export default App;
```

## 2.2 Screens

### File: `app_skeleton/ui/react_frontend/src/screens/OrdersHubScreen.jsx`

```jsx
import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';

import TasksScreen from './TasksScreen';
import LabSectionTwinPanel from '../components/LabSectionTwinPanel.jsx';
import OrdersBillingBrowser from '../components/OrdersBillingBrowser.jsx';
import OrdersArchiveBrowser from '../components/OrdersArchiveBrowser.jsx';
import OrdersSpacePanel from '../components/OrdersSpacePanel.jsx';
import { ClipboardList, Link2 } from 'lucide-react';
import { billingInstructions } from '../data/billingInstructions.js';

/**
 * Orders / Billing / Logistics panels
 * Professional document blueprint hub:
 * - Abort-safe API loading
 * - Robust document normalization
 * - Professional blueprint side navigation
 * - Category-level summaries
 * - Rich document cards with confidence, field/table counts, review status
 * - Search context and sidebar stats
 * - Safer rendering for missing/malformed data
 * - Sensitive values hidden by default
 * - Masked raw source drawer
 * - Preserves existing public exports
 */

const CATEGORY_ORDER = ['billing', 'order_form', 'shipping', 'courier', 'other'];

const CATEGORY_META = {
  billing: {
    id: 'billing',
    label: 'Billing & Invoicing',
    icon: '💳',
    tone: 'blue',
  },
  order_form: {
    id: 'order_form',
    label: 'Order Forms',
    icon: '📋',
    tone: 'violet',
  },
  shipping: {
    id: 'shipping',
    label: 'Customs & Shipping',
    icon: '✈️',
    tone: 'cyan',
  },
  courier: {
    id: 'courier',
    label: 'Courier Accounts',
    icon: '🚚',
    tone: 'green',
  },
  other: {
    id: 'other',
    label: 'Other Documents',
    icon: '📄',
    tone: 'slate',
  },
};

const SENSITIVE_LABEL_PATTERN =
  /\b(password|passcode|secret|secret question|answer|token|api key|apikey|private key|credential|recovery|security question)\b/i;

const SENSITIVE_VALUE_PATTERN =
  /\b(REDACTED|BEGIN PRIVATE KEY|sk-[a-zA-Z0-9]|token=|password=|passwd=)\b/i;

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function toText(value, fallback = '') {
  if (value == null) return fallback;
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);

  if (Array.isArray(value)) {
    return value.map((item) => toText(item)).filter(Boolean).join(', ');
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return fallback;
  }
}

function compactText(value, fallback = '') {
  return toText(value, fallback).replace(/\s+/g, ' ').trim();
}

function titleCaseFromKey(value) {
  return compactText(value)
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function clampNumber(value, min, max, fallback) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function buildApiUrl(baseUrl, path) {
  const cleanBase = compactText(baseUrl).replace(/\/+$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

function getRawDocumentId(doc) {
  return (
    doc?.document_id ||
    doc?.id ||
    doc?.document?.document_id ||
    doc?.document?.id ||
    doc?.metadata?.document_id ||
    doc?.source?.document_id ||
    null
  );
}

function getStableDocId(doc, index) {
  const rawId = getRawDocumentId(doc);
  if (rawId) return String(rawId);

  const fileName =
    doc?.source?.file_name ||
    doc?.document?.source?.file_name ||
    doc?.file_name ||
    'document';

  const title =
    doc?.content?.title ||
    doc?.document?.title ||
    doc?.subject ||
    doc?.name ||
    'untitled';

  return `${compactText(fileName, 'file')}-${compactText(title, 'doc')}-${index}`;
}

function getDocumentType(doc) {
  return compactText(
    doc?.classification?.document_type ||
      doc?.document_type ||
      doc?.document?.classification?.document_type ||
      doc?.document?.document_type ||
      doc?.type ||
      '',
  ).toLowerCase();
}

function getCategoryFromDoc(doc) {
  const docType = getDocumentType(doc);
  const searchable = [
    docType,
    doc?.content?.title,
    doc?.document?.title,
    doc?.subject,
    doc?.source?.file_name,
    doc?.document?.source?.file_name,
    doc?.file_name,
  ]
    .map((item) => compactText(item).toLowerCase())
    .join(' ');

  if (
    docType === 'billing_instruction' ||
    searchable.includes('billing') ||
    searchable.includes('invoice') ||
    searchable.includes('invoicing')
  ) {
    return CATEGORY_META.billing;
  }

  if (
    docType === 'order_form' ||
    searchable.includes('order form') ||
    searchable.includes('purchase order')
  ) {
    return CATEGORY_META.order_form;
  }

  if (
    docType === 'shipping_customs_statement' ||
    searchable.includes('customs') ||
    searchable.includes('shipping') ||
    searchable.includes('shipment') ||
    searchable.includes('usda') ||
    searchable.includes('fedex')
  ) {
    return CATEGORY_META.shipping;
  }

  if (
    docType.startsWith('courier_service') ||
    docType.includes('courier') ||
    searchable.includes('courier') ||
    searchable.includes('fedex') ||
    searchable.includes('dhl') ||
    searchable.includes('ups')
  ) {
    return CATEGORY_META.courier;
  }

  return CATEGORY_META.other;
}

function getDocTitle(doc) {
  return compactText(
    doc?.content?.title ||
      doc?.document?.title ||
      doc?.title ||
      doc?.subject ||
      getRawDocumentId(doc),
    'Untitled document',
  );
}

function getDocSummary(doc) {
  return compactText(
    doc?.content?.short_summary ||
      doc?.document?.short_summary ||
      doc?.summary ||
      doc?.description ||
      doc?.subject,
    '',
  );
}

function getDocFileName(doc) {
  return compactText(
    doc?.source?.file_name ||
      doc?.document?.source?.file_name ||
      doc?.file_name ||
      doc?.source_file ||
      'Unknown file',
  );
}

function getDocLanguage(doc) {
  const language =
    doc?.language?.original ||
    doc?.language?.detected ||
    doc?.document?.language?.original ||
    doc?.document?.language ||
    doc?.language ||
    'en';

  if (isObject(language)) return 'EN';
  return compactText(language, 'en').slice(0, 8).toUpperCase();
}

function getDocConfidence(doc) {
  return clampNumber(
    doc?.classification?.confidence ??
      doc?.document?.classification?.confidence ??
      doc?.confidence,
    0,
    1,
    0.9,
  );
}

function getDocSections(doc) {
  return asArray(
    doc?.gui_display?.sections ||
      doc?.document?.gui_display?.sections ||
      doc?.sections,
  ).filter(Boolean);
}

function getDocTables(doc) {
  return asArray(
    doc?.structured_data?.tables ||
      doc?.document?.structured_data?.tables ||
      doc?.tables,
  ).filter(Boolean);
}

function getRawText(doc) {
  return (
    doc?.content?.original_text ||
    doc?.content?.canonical_text ||
    doc?.document?.content?.original_text ||
    doc?.document?.content?.canonical_text ||
    doc?.original_text ||
    doc?.canonical_text ||
    ''
  );
}

function flattenForSearch(value, depth = 0) {
  if (depth > 5 || value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);

  if (Array.isArray(value)) {
    return value.map((item) => flattenForSearch(item, depth + 1)).join(' ');
  }

  if (isObject(value)) {
    return Object.values(value)
      .map((item) => flattenForSearch(item, depth + 1))
      .join(' ');
  }

  return '';
}

function isSensitiveField(field) {
  const label = compactText(field?.label || field?.name || field?.key);
  const value = compactText(field?.value);

  return (
    SENSITIVE_LABEL_PATTERN.test(label) ||
    SENSITIVE_VALUE_PATTERN.test(value)
  );
}

function maskSensitiveText(rawText) {
  const text = toText(rawText);
  if (!text) return '';

  return text
    .split('\n')
    .map((line) => {
      if (SENSITIVE_LABEL_PATTERN.test(line) || SENSITIVE_VALUE_PATTERN.test(line)) {
        const separatorIndex = line.search(/[:=]/);
        if (separatorIndex >= 0) {
          return `${line.slice(0, separatorIndex + 1)} [hidden]`;
        }
        return '[hidden sensitive line]';
      }

      return line;
    })
    .join('\n');
}

function formatDateTime(value) {
  const text = compactText(value);
  if (!text) return '';

  const date = new Date(text);
  if (Number.isNaN(date.getTime())) return text;

  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  } catch {
    return text;
  }
}

function normalizeDocument(doc, index) {
  const category = getCategoryFromDoc(doc);
  const sections = getDocSections(doc);
  const tables = getDocTables(doc);
  const rawText = getRawText(doc);

  const searchableText = [
    getRawDocumentId(doc),
    getDocTitle(doc),
    getDocSummary(doc),
    getDocFileName(doc),
    getDocumentType(doc),
    category.label,
    getDocLanguage(doc),
    flattenForSearch(sections),
    flattenForSearch(tables),
    rawText,
  ]
    .map((item) => compactText(item).toLowerCase())
    .join(' ');

  return {
    id: getStableDocId(doc, index),
    raw: doc,
    title: getDocTitle(doc),
    summary: getDocSummary(doc),
    fileName: getDocFileName(doc),
    language: getDocLanguage(doc),
    category,
    documentType: getDocumentType(doc),
    confidence: getDocConfidence(doc),
    needsReview:
      Boolean(doc?.quality?.needs_human_review) ||
      Boolean(doc?.document?.quality?.needs_human_review),
    sections,
    tables,
    rawText,
    searchableText,
  };
}

function getDocumentFieldCount(doc) {
  return asArray(doc?.sections).reduce((total, section) => {
    return total + asArray(section?.fields).length;
  }, 0);
}

function getDocumentTableCount(doc) {
  return asArray(doc?.tables).length;
}

function getDocumentTypeLabel(doc) {
  if (doc?.documentType) return titleCaseFromKey(doc.documentType);
  return 'Blueprint';
}

function HighlightedCount({ count, total }) {
  return (
    <span className="obp-count" aria-label={`${count} of ${total} documents visible`}>
      {count === total ? `(${total})` : `(${count}/${total})`}
    </span>
  );
}

function SidebarBlueprintStats({ docs, filteredDocs, searchQuery }) {
  const total = docs.length;
  const visible = filteredDocs.length;
  const reviewCount = docs.filter((doc) => doc.needsReview).length;
  const structuredCount = docs.filter(
    (doc) => doc.sections.length || doc.tables.length,
  ).length;
  const categoryCount = CATEGORY_ORDER.filter((categoryId) =>
    docs.some((doc) => doc.category?.id === categoryId),
  ).length;

  return (
    <div className="obp-sidebar-stats" aria-label="Document blueprint summary">
      <div className="obp-sidebar-stat-card">
        <span className="obp-sidebar-stat-value">{visible}</span>
        <span className="obp-sidebar-stat-label">
          {searchQuery ? 'Visible' : 'Blueprints'}
        </span>
      </div>

      <div className="obp-sidebar-stat-card">
        <span className="obp-sidebar-stat-value">{categoryCount}</span>
        <span className="obp-sidebar-stat-label">Categories</span>
      </div>

      <div className="obp-sidebar-stat-card">
        <span className="obp-sidebar-stat-value">{structuredCount}</span>
        <span className="obp-sidebar-stat-label">Structured</span>
      </div>

      {reviewCount ? (
        <div className="obp-sidebar-stat-card has-warning">
          <span className="obp-sidebar-stat-value">{reviewCount}</span>
          <span className="obp-sidebar-stat-label">Review</span>
        </div>
      ) : null}

      {searchQuery ? (
        <div className="obp-sidebar-stat-card obp-sidebar-stat-card--wide">
          <span className="obp-sidebar-stat-value">{visible}/{total}</span>
          <span className="obp-sidebar-stat-label">Search result</span>
        </div>
      ) : null}
    </div>
  );
}

function SecretValue({ value }) {
  const [revealed, setRevealed] = useState(false);
  const text = compactText(value, '—');

  return (
    <span className="obp-secret-wrap">
      <span className="obp-secret" title={revealed ? undefined : 'Hidden sensitive value'}>
        🔒 {revealed ? text : 'Hidden sensitive value'}
      </span>
      <button
        type="button"
        className="obp-inline-action"
        onClick={() => setRevealed((current) => !current)}
        aria-label={revealed ? 'Hide sensitive value' : 'Reveal sensitive value'}
      >
        {revealed ? 'Hide' : 'Reveal'}
      </button>
    </span>
  );
}

function FieldValue({ field }) {
  const value = field?.value ?? field?.text ?? field?.content ?? '';
  const text = compactText(value, '—');

  if (isSensitiveField(field)) {
    return <SecretValue value={text} />;
  }

  if (/^https?:\/\//i.test(text)) {
    return (
      <a
        href={text}
        className="obp-field-link"
        target="_blank"
        rel="noreferrer"
      >
        {text}
      </a>
    );
  }

  return <>{text}</>;
}


function OrdersArchiveSpotlight({ context = 'default' }) {
  const contextCopy = {
    empty: {
      eyebrow: 'Archive fallback',
      title: 'Orders Archive Still Available',
      body: 'The live billing blueprint API did not return records, but the historical orders archive can still be reviewed from the lab twin.',
    },
    error: {
      eyebrow: 'Archive safety layer',
      title: 'Use the Archive While Live Blueprints Recover',
      body: 'The live endpoint is unavailable. Historical purchase orders and procurement records remain accessible from the processed archive.',
    },
    default: {
      eyebrow: 'Historical procurement intelligence',
      title: 'Orders Archive',
      body: 'Review historical purchase orders, procurement traces, reagent requests, sequencing orders, service records, and lab operational follow-ups.',
    },
  };

  const copy = contextCopy[context] || contextCopy.default;

  return (
    <section className="obp-archive-shell" aria-label="Orders archive">
      <div className="panel obp-archive-hero">
        <div className="obp-archive-hero-copy">
          <p className="text-caption">{copy.eyebrow}</p>
          <h3 className="obp-archive-title">{copy.title}</h3>
          <p className="text-body-secondary obp-archive-lead">
            {copy.body}
          </p>
        </div>

        <div className="obp-archive-scoreboard" aria-label="Archive coverage summary">
          <div className="obp-archive-score-card">
            <span className="obp-archive-score-value">PO</span>
            <span className="obp-archive-score-label">Purchase orders</span>
          </div>
          <div className="obp-archive-score-card">
            <span className="obp-archive-score-value">Vendor</span>
            <span className="obp-archive-score-label">Supplier records</span>
          </div>
          <div className="obp-archive-score-card">
            <span className="obp-archive-score-value">Trace</span>
            <span className="obp-archive-score-label">Audit context</span>
          </div>
        </div>
      </div>

      <div className="obp-archive-layout">
        <aside className="panel obp-archive-sidebar">
          <p className="text-caption">Archive workflow</p>
          <h4 className="text-title-3">Review checklist</h4>

          <ol className="obp-archive-steps">
            <li>
              <span className="obp-archive-step-index">01</span>
              <span>
                <strong>Find the original record</strong>
                <small>Search by vendor, order code, project, reagent, sequencing batch, or service type.</small>
              </span>
            </li>
            <li>
              <span className="obp-archive-step-index">02</span>
              <span>
                <strong>Check operational context</strong>
                <small>Compare archive notes with live billing blueprints, customs files, and courier instructions.</small>
              </span>
            </li>
            <li>
              <span className="obp-archive-step-index">03</span>
              <span>
                <strong>Use traceability carefully</strong>
                <small>Confirm sample, shipment, invoice, and project links before reusing historical details.</small>
              </span>
            </li>
          </ol>

          <div className="obp-archive-note">
            <strong>Best use:</strong> historical lookup, audit support, vendor history, and procurement continuity.
          </div>
        </aside>

        <div className="obp-archive-main">
          <LabSectionTwinPanel
            sectionId="orders_archive"
            title="Orders archive"
            description="Historical purchase orders, procurement records, and archived operational order documents."
            excludeFolder="Billing"
          />
        </div>
      </div>
    </section>
  );
}


function LoadingState() {
  return (
    <div className="obp-shell" aria-busy="true">
      <div className="panel obp-header obp-header--loading">
        <div>
          <p className="text-caption">Orders intelligence</p>
          <h2 className="text-title-1 obp-title">Loading logistics blueprints…</h2>
          <p className="page-lead obp-lead">
            Preparing courier, customs, order, and billing instructions.
          </p>
        </div>
      </div>

      <div className="obp-layout">
        <div className="panel obp-master obp-blueprints-sidebar feed-scroll">
          <div className="obp-skeleton obp-skeleton--title" />
          <div className="obp-skeleton obp-skeleton--card" />
          <div className="obp-skeleton obp-skeleton--card" />
          <div className="obp-skeleton obp-skeleton--card" />
        </div>

        <div className="panel obp-detail">
          <div className="obp-skeleton obp-skeleton--hero" />
          <div className="obp-sections-grid">
            <div className="obp-skeleton obp-skeleton--section" />
            <div className="obp-skeleton obp-skeleton--section" />
            <div className="obp-skeleton obp-skeleton--section" />
            <div className="obp-skeleton obp-skeleton--section" />
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyDocumentsState({ onRetry }) {
  return (
    <div className="stack-md">
      <div className="panel obp-empty-panel">
        <p className="text-caption">No documents found</p>
        <h2 className="text-title-1">No logistics or billing blueprints loaded</h2>
        <p className="text-body-secondary">
          The API responded successfully, but no document records were returned.
        </p>
        <button type="button" className="button button-primary" onClick={onRetry}>
          Reload documents
        </button>
      </div>

      <OrdersArchiveSpotlight context="empty" />
    </div>
  );
}

function ErrorState({ error, endpoint, onRetry }) {
  return (
    <div className="stack-md">
      <div className="panel panel-danger obp-error-panel" role="alert">
        <p className="text-caption">Orders API unavailable</p>
        <h2 className="text-title-2">Could not load billing instructions</h2>
        <p>{error || 'Unknown loading error.'}</p>

        <div className="obp-error-meta">
          <span className="text-caption">Endpoint</span>
          <code>{endpoint}</code>
        </div>

        <button type="button" className="button button-primary" onClick={onRetry}>
          Try again
        </button>
      </div>

      <OrdersArchiveSpotlight context="error" />
    </div>
  );
}

function CategoryGroup({ category, documents, selectedDocId, onSelectDocument }) {
  if (!documents.length) return null;

  const categoryConfidence = documents.length
    ? Math.round(
        (documents.reduce((total, doc) => total + Number(doc.confidence || 0), 0) /
          documents.length) *
          100,
      )
    : 0;

  return (
    <section
      className="obp-cat-group obp-cat-group--premium"
      aria-label={category.label}
      data-category={category.id}
    >
      <div className="obp-cat-header obp-cat-header--premium" data-category={category.id}>
        <div className="obp-cat-heading-left">
          <span className="obp-cat-icon obp-cat-icon--premium" aria-hidden="true">
            {category.icon}
          </span>

          <span className="obp-cat-copy">
            <span className="obp-cat-title">{category.label}</span>
            <span className="obp-cat-subtitle">
              {documents.length} document{documents.length === 1 ? '' : 's'} · {categoryConfidence}% avg confidence
            </span>
          </span>
        </div>

        <span className="obp-cat-count obp-cat-count--premium">
          {documents.length}
        </span>
      </div>

      <div className="obp-cat-doc-stack">
        {documents.map((doc) => {
          const isSelected = doc.id === selectedDocId;
          const fieldCount = getDocumentFieldCount(doc);
          const tableCount = getDocumentTableCount(doc);
          const confidence = Math.round((doc.confidence || 0) * 100);

          return (
            <button
              type="button"
              key={doc.id}
              onClick={() => onSelectDocument(doc.id)}
              className={`obp-doc-item obp-doc-item--premium${isSelected ? ' is-active' : ''}`}
              data-category={category.id}
              aria-current={isSelected ? 'true' : undefined}
              aria-label={`Open ${doc.title}`}
            >
              <span className="obp-doc-active-rail" aria-hidden="true" />

              <span className="obp-doc-card-topline">
                <span className="obp-doc-type-chip">
                  {getDocumentTypeLabel(doc)}
                </span>

                <span className="obp-doc-confidence-mini">
                  {confidence}%
                </span>
              </span>

              <span className="obp-doc-title">{doc.title}</span>

              {doc.summary ? (
                <span className="obp-doc-summary">{doc.summary}</span>
              ) : (
                <span className="obp-doc-summary is-muted">
                  Structured operational document from {doc.fileName}.
                </span>
              )}

              <span className="obp-doc-meta obp-doc-meta--premium">
                <span className="obp-doc-file" title={doc.fileName}>
                  {doc.fileName}
                </span>

                <span className="obp-doc-pill">{doc.language}</span>

                {fieldCount > 0 ? (
                  <span className="obp-doc-pill">{fieldCount} fields</span>
                ) : null}

                {tableCount > 0 ? (
                  <span className="obp-doc-pill">
                    {tableCount} table{tableCount === 1 ? '' : 's'}
                  </span>
                ) : null}

                {doc.needsReview ? (
                  <span className="obp-doc-review">Review</span>
                ) : (
                  <span className="obp-doc-pill is-structured">Structured</span>
                )}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function DocumentSections({ document }) {
  if (!document.sections.length) {
    return (
      <div className="obp-empty-detail-card">
        <h4 className="text-title-3">No structured display sections</h4>
        <p className="text-body-secondary">
          This document does not include GUI display fields yet. Use the masked raw source below
          to inspect extracted text.
        </p>
      </div>
    );
  }

  return (
    <div className="obp-sections-grid">
      {document.sections.map((section, sectionIndex) => {
        const sectionTitle = compactText(
          section?.section_title || section?.title || section?.name,
          `Section ${sectionIndex + 1}`,
        );

        const fields = asArray(section?.fields);
        const isQuality = /quality|review|warning|issue/i.test(sectionTitle);

        return (
          <section
            key={`${sectionTitle}-${sectionIndex}`}
            className={`obp-section${isQuality ? ' obp-section--warning obp-section--full' : ''}`}
          >
            <h4 className="obp-section-title">
              {isQuality ? <span aria-hidden="true">⚠️ </span> : null}
              {sectionTitle}
            </h4>

            {fields.length ? (
              <div className="obp-fields">
                {fields.map((field, fieldIndex) => {
                  const label = compactText(
                    field?.label || field?.name || field?.key,
                    `Field ${fieldIndex + 1}`,
                  );

                  return (
                    <div key={`${label}-${fieldIndex}`} className="obp-field">
                      <span className="obp-field-label">{label}</span>
                      <span className="obp-field-value">
                        <FieldValue field={field} />
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-body-secondary">
                No fields were extracted for this section.
              </p>
            )}
          </section>
        );
      })}
    </div>
  );
}

function DocumentTables({ tables }) {
  if (!tables.length) return null;

  return (
    <>
      {tables.map((table, tableIndex) => {
        const tableName = titleCaseFromKey(table?.name || `Table ${tableIndex + 1}`);
        const columns = asArray(table?.column_names || table?.columns);
        const rows = asArray(table?.rows);

        if (!columns.length && !rows.length) return null;

        const inferredColumns =
          columns.length ||
          !rows.length ||
          !isObject(rows[0])
            ? columns
            : Object.keys(rows[0]);

        return (
          <section key={`${tableName}-${tableIndex}`} className="obp-table-wrap">
            <h4 className="obp-table-title">📋 {tableName}</h4>

            <div className="obp-table-scroll">
              <table className="table obp-table">
                <thead>
                  <tr>
                    {inferredColumns.map((column, columnIndex) => (
                      <th key={`${column}-${columnIndex}`} className="obp-th">
                        {titleCaseFromKey(column)}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {rows.length ? (
                    rows.map((row, rowIndex) => (
                      <tr key={`row-${rowIndex}`}>
                        {inferredColumns.map((column, columnIndex) => (
                          <td key={`${column}-${columnIndex}`} className="obp-td">
                            {isObject(row)
                              ? compactText(row[column], '—')
                              : compactText(row, '—')}
                          </td>
                        ))}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="obp-td" colSpan={Math.max(inferredColumns.length, 1)}>
                        No table rows extracted.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
    </>
  );
}

function RawSourceDrawer({ rawText }) {
  const maskedText = maskSensitiveText(rawText);

  if (!maskedText) return null;

  return (
    <details className="obp-raw-drawer">
      <summary className="obp-raw-summary">
        🔍 View masked raw extracted text source
      </summary>

      <p className="text-caption obp-raw-warning">
        Sensitive-looking lines are hidden automatically. Use the structured fields above
        for normal work.
      </p>

      <pre className="code-block obp-raw-pre">{maskedText}</pre>
    </details>
  );
}

function DocumentDetail({ document, searchQuery }) {
  if (!document) {
    return (
      <div className="obp-empty-detail">
        <p className="text-caption">
          {searchQuery ? 'No matching blueprint selected' : 'Nothing selected'}
        </p>
        <h3 className="text-title-2">
          {searchQuery ? 'No document matches this search' : 'Select a document'}
        </h3>
        <p className="text-body-secondary">
          {searchQuery
            ? 'Try a different keyword, filename, field value, courier name, or document ID.'
            : 'Choose a document from the left panel to inspect extracted fields, tables, and source text.'}
        </p>
      </div>
    );
  }

  return (
    <article className="obp-detail-inner" aria-labelledby="orders-document-title">
      <header className="obp-detail-header">
        <div className="obp-detail-badges">
          <span
            className={`obp-badge obp-badge--${document.category.tone || 'blue'}`}
          >
            <span aria-hidden="true">{document.category.icon}</span>&nbsp;
            {document.category.label}
          </span>

          <span className="obp-badge obp-badge--green">
            Confidence: {Math.round(document.confidence * 100)}%
          </span>

          {document.needsReview ? (
            <span className="obp-badge obp-badge--amber">
              ⚠️ Review Required
            </span>
          ) : (
            <span className="obp-badge obp-badge--blue">
              Structured
            </span>
          )}
        </div>

        <h3 id="orders-document-title" className="obp-detail-title">
          {document.title}
        </h3>

        {document.summary ? (
          <p className="page-lead">{document.summary}</p>
        ) : (
          <p className="page-lead">
            Extracted operational document from {document.fileName}.
          </p>
        )}

        <div className="obp-detail-meta">
          <span>
            <strong>File:</strong> {document.fileName}
          </span>
          <span>
            <strong>Language:</strong> {document.language}
          </span>
          {document.documentType ? (
            <span>
              <strong>Type:</strong> {titleCaseFromKey(document.documentType)}
            </span>
          ) : null}
        </div>
      </header>

      <DocumentSections document={document} />
      <DocumentTables tables={document.tables} />
      <RawSourceDrawer rawText={document.rawText} />
    </article>
  );
}

function OrdersBillingPanel({ API_URL }) {
  const [documents, setDocuments] = useState([]);
  const [filteredDocs, setFilteredDocs] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loadState, setLoadState] = useState({ phase: 'loading' });
  const [error, setError] = useState(null);

  const fetchDocuments = useCallback(async () => {
    setLoadState({ phase: 'loading' });
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/billing-instructions`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      const docs = (data.documents || []).map((doc, index) => normalizeDocument(doc, index));
      setDocuments(docs);
      setFilteredDocs(docs);
      setLoadState({ phase: 'ready' });
    } catch (err) {
      setError(err.message);
      setLoadState({ phase: 'error' });
    }
  }, [API_URL]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredDocs(documents);
      return;
    }

    const tokens = searchQuery.toLowerCase().split(/\s+/).filter(Boolean);
    const filtered = documents.filter((doc) => {
      const searchable = doc.searchableText || '';
      return tokens.every((token) => searchable.includes(token));
    });
    setFilteredDocs(filtered);
  }, [searchQuery, documents]);

  const groupedDocs = useMemo(() => {
    const groups = {};
    CATEGORY_ORDER.forEach((catId) => {
      groups[catId] = [];
    });

    filteredDocs.forEach((doc) => {
      const catId = doc.category?.id || 'other';
      if (groups[catId]) {
        groups[catId].push(doc);
      }
    });

    return groups;
  }, [filteredDocs]);

  if (loadState.phase === 'loading') {
    return <LoadingState />;
  }

  if (loadState.phase === 'error') {
    return <ErrorState error={error} endpoint="/api/billing-instructions" onRetry={fetchDocuments} />;
  }

  if (!documents.length && loadState.phase === 'ready') {
    return <EmptyDocumentsState onRetry={fetchDocuments} />;
  }

  const selectedDoc = documents.find((doc) => doc.id === selectedDocId) || null;

  return (
    <div className="obp-shell">
      <div className="panel obp-header">
        <div>
          <p className="text-caption">Orders intelligence</p>
          <h2 className="text-title-1 obp-title">Billing & Ordering Blueprints</h2>
          <p className="page-lead obp-lead">
            Structured billing instructions, order forms, shipping documents, and courier accounts.
          </p>
        </div>

        <div className="obp-header-actions">
          <input
            type="text"
            className="obp-search-input"
            placeholder="Search blueprints..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search billing and ordering documents"
          />
        </div>
      </div>

      <div className="obp-layout">
        <div className="panel obp-master obp-blueprints-sidebar feed-scroll">
          <SidebarBlueprintStats
            docs={documents}
            filteredDocs={filteredDocs}
            searchQuery={searchQuery}
          />

          {CATEGORY_ORDER.map((catId) => {
            const category = CATEGORY_META[catId];
            const docs = groupedDocs[catId] || [];
            if (!docs.length) return null;

            return (
              <CategoryGroup
                key={catId}
                category={category}
                documents={docs}
                selectedDocId={selectedDocId}
                onSelectDocument={setSelectedDocId}
              />
            );
          })}
        </div>

        <div className="panel obp-detail">
          <DocumentDetail document={selectedDoc} searchQuery={searchQuery} />
        </div>
      </div>
    </div>
  );
}

function OrdersArchivePanel() {
  return <OrdersArchiveSpotlight context="default" />;
}

function OrdersRegisterPanel() {
  return (
    <div className="panel">
      <h2 className="text-title-2">Orders Register</h2>
      <p className="text-body-secondary">Order registration panel - coming soon.</p>
    </div>
  );
}

function OrdersRelatedPanel({ auditLogs }) {
  return (
    <div className="panel">
      <h2 className="text-title-2">Related Documents</h2>
      <p className="text-body-secondary">Related documents panel - coming soon.</p>
    </div>
  );
}

function OrdersTasksPanel({ ...props }) {
  return <TasksScreen {...props} hideHeader />;
}

export {
  OrdersTasksPanel,
  OrdersRegisterPanel,
  OrdersRelatedPanel,
  OrdersBillingPanel,
  OrdersArchivePanel,
};
```

## 2.3 Components

### File: `app_skeleton/ui/react_frontend/src/components/OrdersBillingBrowser.jsx`

```jsx
import { CreditCard, FileText, FolderOpen, Lock, Plane, Shield, Truck } from 'lucide-react';
import LabDocumentsBrowser from './LabDocumentsBrowser.jsx';
import {
  BILLING_CATEGORY_GROUPS,
  billingDocumentTitle,
  categorizeBillingPath,
} from '../utils/ordersBillingCategories.js';

const CATEGORY_ICONS = {
  general_reference: FileText,
  hus_finance: CreditCard,
  credentials: Lock,
  fedex: Plane,
  ups: Truck,
  dna_shipments: FileText,
  us_customs: Shield,
  other_admin: FolderOpen,
};

export default function OrdersBillingBrowser() {
  return (
    <LabDocumentsBrowser
      sectionId="orders_billing"
      title="Billing & Ordering Instructions"
      description="Billing addresses, vendor accounts, shipments, and HUS billing."
      icon={CreditCard}
      categoryGroups={BILLING_CATEGORY_GROUPS}
      defaultCategory="general_reference"
      categorizePath={(path) => categorizeBillingPath(path)}
      documentTitle={billingDocumentTitle}
      categoryIcons={CATEGORY_ICONS}
      className="orders-billing-browser catalog-space-browser"
      sensitiveCategories={['credentials']}
    />
  );
}
```

### File: `app_skeleton/ui/react_frontend/src/components/LabDocumentsBrowser.jsx`

```jsx
import { useEffect, useMemo, useState } from 'react';
import { FileText, Loader2, Lock } from 'lucide-react';
import DocumentPreviewPane from './DocumentPreviewPane.jsx';
import DocumentFileSearch from './DocumentFileSearch.jsx';
import SmartLink from './SmartLink.jsx';
import {
  documentDisplayExcerpt,
  fetchLabSectionProcessed,
  getChunkTextForFile,
  labDatabaseAssetUrl,
} from '../utils/labDatabaseUtils.js';
import { isJunkPreviewText } from '../utils/textCleanup.js';
import { inferExtension } from '../utils/fileTypeMeta.js';
import { getMediaPreviewKind } from '../utils/mediaPreviewKind.js';
import { buildMediaGallery, mergeGalleryItem } from '../utils/mediaGalleryUtils.js';
import { useSpreadsheetPreview } from '../hooks/useSpreadsheetPreview.js';
import { useRawFilePreview } from '../hooks/useRawFilePreview.js';
import { useCatalogDocumentPreview } from '../hooks/useCatalogDocumentPreview.js';
import { getFilePreviewKind } from '../utils/filePreviewKind.js';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';
import {
  collectProjectDocuments,
  deduplicateDocumentsByPath,
  flattenCategoryOrder,
  groupDocumentsByCategory,
} from '../utils/documentBrowserUtils.js';
import { normalizeDocPath } from '../utils/folderBrowserUtils.js';
import DocumentCategoryFileList, {
  countGroupedFiles,
} from './DocumentCategoryFileList.jsx';
import { useGuiT } from '../i18n/useGuiT.js';
import { useModuleShellHeaderSlot } from '../contexts/ModuleShellHeaderSlotContext.jsx';
import { consumeSearchNavigation } from '../utils/searchHits.js';

export default function LabDocumentsBrowser({
  sectionId,
  sectionIds,
  title: _title,
  description: _description,
  icon: _Icon = FileText,
  categoryGroups,
  defaultCategory,
  categorizePath,
  documentTitle,
  categoryIcons = {},
  className = 'lab-documents-browser',
  topPanel = null,
  sensitiveCategories = [],
  documentFilter = null,
  syntheticDocs = [],
  syntheticPreviewField = 'inlineContent',
  folderHintResolver = null,
  layoutVariant = 'catalog',
}) {
  const [twins, setTwins] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPath, setSelectedPath] = useState(null);
  const [fileQuery, setFileQuery] = useState('');
  const [revealSensitive, setRevealSensitive] = useState(false);
  const { openTaskpad } = useTaskpad();
  const { t, localizeCategories } = useGuiT();

  const ids = sectionIds?.length ? sectionIds : [sectionId];

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    Promise.all(ids.map((id) => fetchLabSectionProcessed(id).then((data) => [id, data])))
      .then((pairs) => {
        if (!mounted) return;
        const loaded = pairs.filter(([, data]) => data);
        const map = Object.fromEntries(loaded);
        if (!Object.keys(map).length) {
          throw new Error('No document sections could be loaded.');
        }
        setTwins(map);
        setLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message || 'Failed to load documents.');
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [ids.join(',')]);

  useEffect(() => {
    if (loading || !Object.keys(twins).length) return;
    const pending = consumeSearchNavigation();
    if (!pending?.relative_path) return;
    const target = normalizeDocPath(pending.relative_path);
    if (pending.query) setFileQuery(pending.query);
    setSelectedPath(target);
  }, [loading, twins]);

  const primaryTwin = twins[ids[0]];

  const allDocs = useMemo(() => {
    const docs = [];
    for (const id of ids) {
      const twin = twins[id];
      if (!twin) continue;
      const sectionDocs = collectProjectDocuments(twin, {
        categorizePath: (path) => categorizePath(path, id),
        documentTitle,
      });
      for (const doc of sectionDocs) {
        if (documentFilter && !documentFilter(doc.path)) continue;
        docs.push({
          ...doc,
          sourceSection: id,
          folderHint:
            folderHintResolver?.(id)
            || (ids.length > 1 ? id.replace('overview_', '').replace(/_/g, ' ') : null),
        });
      }
    }
    for (const doc of syntheticDocs) {
      if (documentFilter && !documentFilter(doc.path)) continue;
      docs.push(doc);
    }
    return deduplicateDocumentsByPath(docs);
  }, [twins, ids, categorizePath, documentTitle, documentFilter, syntheticDocs, folderHintResolver]);

  const localizedCategoryGroups = useMemo(
    () => localizeCategories(categoryGroups),
    [categoryGroups, localizeCategories]
  );

  const categoryOrder = useMemo(
    () => flattenCategoryOrder(localizedCategoryGroups),
    [localizedCategoryGroups]
  );
  const grouped = useMemo(
    () => groupDocumentsByCategory(allDocs, categoryOrder),
    [allDocs, categoryOrder]
  );

  const visibleFileCount = useMemo(
    () =>
      countGroupedFiles(localizedCategoryGroups, grouped, fileQuery, documentTitle),
    [localizedCategoryGroups, grouped, fileQuery, documentTitle]
  );

  const setHeaderSlot = useModuleShellHeaderSlot();

  useEffect(() => {
    if (!setHeaderSlot) return undefined;
    setHeaderSlot(
      <DocumentFileSearch
        value={fileQuery}
        onChange={setFileQuery}
        fileCount={visibleFileCount}
        searchPlaceholder={t('docs.searchPlaceholder')}
        searchAria={t('docs.searchFiles')}
        filesLabel={t('docs.filesInSection', '', { count: visibleFileCount })}
      />
    );
    return () => setHeaderSlot(null);
  }, [setHeaderSlot, fileQuery, visibleFileCount, t]);

  const selectedDoc = useMemo(() => {
    if (!selectedPath) return null;
    const key = normalizeDocPath(selectedPath);
    return allDocs.find((d) => normalizeDocPath(d.path) === key) || null;
  }, [allDocs, selectedPath]);

  const selectedCategoryId = selectedDoc?.categoryId;
  const isSensitive = sensitiveCategories.includes(selectedCategoryId);

  const selectedTwin = selectedDoc?.sourceSection
    ? twins[selectedDoc.sourceSection]
    : primaryTwin;

  const maskSensitiveText = (text) => {
    if (!text) return '';
    return text
      .split('\n')
      .map((line) => {
        if (/\b(password|passcode|secret|username|credential|token|api key)\b/i.test(line)) {
          const sep = line.search(/[:=]/);
          if (sep >= 0) return `${line.slice(0, sep + 1)} [hidden]`;
          return '[hidden sensitive line]';
        }
        return line;
      })
      .join('\n');
  };

  const selectedExt = selectedDoc
    ? inferExtension(selectedDoc.name, selectedDoc.extension)
    : '';
  const isPdf = selectedExt === '.pdf';
  const mediaKind = getMediaPreviewKind(selectedExt);
  const previewKind = getFilePreviewKind(selectedExt, selectedDoc?.path);
  const isSpreadsheet = previewKind === 'spreadsheet';

  const relativeRoot = selectedTwin?.relative_root || primaryTwin?.relative_root;
  const assetUrl = useMemo(
    () =>
      selectedDoc && relativeRoot
        ? labDatabaseAssetUrl(relativeRoot, selectedDoc.path)
        : null,
    [selectedDoc, relativeRoot]
  );

  const twinPreviewText = useMemo(() => {
    if (!selectedDoc) return null;
    if (selectedDoc.isSynthetic && selectedDoc[syntheticPreviewField]) {
      const raw = String(selectedDoc[syntheticPreviewField]).trim();
      return isSensitive && !revealSensitive ? maskSensitiveText(raw) : raw;
    }
    if (!selectedTwin) return null;
    const fromChunks = getChunkTextForFile(selectedTwin, selectedDoc.path);
    const excerpt = selectedDoc.excerpt || documentDisplayExcerpt(selectedDoc, 12000);
    const raw = (fromChunks || excerpt || '').trim();
    
    return isSensitive && !revealSensitive ? maskSensitiveText(raw) : raw;
  }, [selectedDoc, selectedTwin, isSensitive, revealSensitive, syntheticPreviewField]);

  if (loading) {
    return (
      <div className="panel" style={{ padding: '2rem', textAlign: 'center' }}>
        <Loader2 size={20} className="spin-inline" /> {t('docs.loading')}
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel" style={{ padding: '2rem', color: 'var(--mac-destructive)' }}>
        {error}
      </div>
    );
  }

  const resolvedLayoutVariant = layoutVariant === 'default' ? 'catalog' : layoutVariant;
  const isSplitCatalogLayout =
    resolvedLayoutVariant === 'protocols' || resolvedLayoutVariant === 'catalog';
  const browserClassName = [
    className,
    isSplitCatalogLayout ? 'catalog-space-browser lab-documents-browser--catalog' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const sensitiveNote = isSensitive ? (
    <p className="lab-doc-sensitive-note">
      <Lock size={14} /> {t('docs.sensitiveMasked')}
    </p>
  ) : null;

  const fileList = (
    <DocumentCategoryFileList
      categoryGroups={localizedCategoryGroups}
      grouped={grouped}
      fileQuery={fileQuery}
      documentTitle={documentTitle}
      selectedPath={selectedPath}
      onSelectFile={setSelectedPath}
      categoryIcons={categoryIcons}
      sensitiveCategories={sensitiveCategories}
      categoryLayout={isSplitCatalogLayout ? 'horizontal-top' : 'inline'}
      renderPreview={
        isSplitCatalogLayout
          ? (fileBody) => (
              <div
                className={`lab-docs-catalog-split pfb-layout lab-docs-layout lab-docs-layout--compact lab-docs-layout--catalog${selectedDoc ? ' pfb-layout--editor-focus pfb-layout--doc-full' : ''}`}
              >
                <div className="pfb-column pfb-files-pane lab-doc-files-panel lab-doc-files-panel--catalog">
                  {sensitiveNote}
                  {fileBody}
                </div>
                <div className="pfb-column pfb-preview-pane pfb-preview-pane--editor-focus">
                  {!selectedDoc ? (
                    <div className="lab-doc-preview-placeholder">
                      <p className="text-footnote muted">{t('docs.selectFile')}</p>
                      {isSplitCatalogLayout ? (
                        <p className="text-footnote muted lab-doc-preview-placeholder-hint">
                          {t('docs.catalogPreviewHint')}
                        </p>
                      ) : null}
                    </div>
                  ) : (
                    <DocumentPreviewPane
                      onBackToFiles={() => setSelectedPath(null)}
                      title={documentTitle(selectedDoc)}
                      path={selectedDoc.path}
                      extension={selectedDoc.extension || inferExtension(selectedDoc.name)}
                      previewKind={previewKind}
                      previewText={twinPreviewText}
                      mediaKind={mediaKind}
                      mediaUrl={assetUrl}
                      mediaAlt={documentTitle(selectedDoc)}
                      onCreateTask={(text) =>
                        openTaskpad(text, {
                          section: sectionId,
                          filePath: selectedPath || undefined,
                          fileName: selectedDoc?.name || selectedDoc?.title,
                        })
                      }
                      actions={
                        <>
                          {assetUrl ? (
                            <a
                              href={assetUrl}
                              className="btn btn-secondary btn-sm"
                              target="_blank"
                              rel="noreferrer"
                            >
                              {t('docs.openOriginal')}
                            </a>
                          ) : null}
                          {isSensitive ? (
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => setRevealSensitive((v) => !v)}
                            >
                              {revealSensitive ? t('docs.hideSensitive') : t('docs.revealSensitive')}
                            </button>
                          ) : null}
                        </>
                      }
                    />
                  )}
                </div>
              </div>
            )
          : null
      }
    />
  );

  return (
    <section className={`panel workspace-section data-pad data-pad--compact data-pad--embedded ${browserClassName}`}>
      {topPanel}

      <div className={`lab-docs-section-layout lab-docs-section-layout--grouped${isSplitCatalogLayout ? ' lab-docs-section-layout--catalog' : ''}`}>
        <div className="lab-docs-section-main">
          {isSplitCatalogLayout ? (
            <div className="lab-docs-catalog-shell">
              {fileList}
            </div>
          ) : (
            <div
              className={`pfb-layout lab-docs-layout lab-docs-layout--compact${selectedDoc ? ' pfb-layout--editor-focus pfb-layout--doc-full' : ''}`}
            >
              <div className="pfb-column pfb-files-pane lab-doc-files-panel">
                {sensitiveNote}
                {fileList}
              </div>
              <div className="pfb-column pfb-preview-pane pfb-preview-pane--editor-focus">
                {!selectedDoc ? (
                  <div className="lab-doc-preview-placeholder">
                    <p className="text-footnote muted">{t('docs.selectFile')}</p>
                  </div>
                ) : (
                  <DocumentPreviewPane
                    onBackToFiles={() => setSelectedPath(null)}
                    title={documentTitle(selectedDoc)}
                    path={selectedDoc.path}
                    extension={selectedDoc.extension || inferExtension(selectedDoc.name)}
                    previewKind={previewKind}
                    previewText={twinPreviewText}
                    mediaKind={mediaKind}
                    mediaUrl={assetUrl}
                    mediaAlt={documentTitle(selectedDoc)}
                    onCreateTask={(text) =>
                      openTaskpad(text, {
                        section: sectionId,
                        filePath: selectedPath || undefined,
                        fileName: selectedDoc?.name || selectedDoc?.title,
                      })
                    }
                    actions={
                      <>
                        {assetUrl ? (
                          <a
                            href={assetUrl}
                            className="btn btn-secondary btn-sm"
                            target="_blank"
                            rel="noreferrer"
                          >
                            {t('docs.openOriginal')}
                          </a>
                        ) : null}
                        {isSensitive ? (
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => setRevealSensitive((v) => !v)}
                          >
                            {revealSensitive ? t('docs.hideSensitive') : t('docs.revealSensitive')}
                          </button>
                        ) : null}
                      </>
                    }
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
```

## 2.4 API Client

### File: `app_skeleton/ui/react_frontend/src/api/client.js`

```javascript
/**
 * Shared API client — base URL from VITE_API_URL, Bearer token when available.
 */

import {
  AUTH_SKIP_HEADER_VALUE,
  isAuthSkipActive,
} from '../utils/authSkip.js';

const TOKEN_KEY = 'farkki_id_token';

export function getApiUrl() {
  // Dev: same-origin so Vite proxies /api → backend (works at localhost:5173 and LAN IP:5173).
  if (import.meta.env.DEV && typeof window !== 'undefined') {
    return '';
  }
  const fromEnv = import.meta.env.VITE_API_URL;
  if (fromEnv && String(fromEnv).trim()) {
    return String(fromEnv).replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    return `http://${window.location.hostname}:8000`;
  }
  return 'http://127.0.0.1:8000';
}

export function getAuthToken() {
  try {
    return window.localStorage.getItem(TOKEN_KEY) || null;
  } catch {
    return null;
  }
}

export function setAuthToken(token) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore
  }
}

export function clearAuthToken() {
  setAuthToken(null);
}

export function apiUrl(path, params) {
  const base = getApiUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const query = params ? `?${params.toString()}` : '';
  return `${base}${cleanPath}${query}`;
}

function buildHeaders(extra = {}, body) {
  const headers = { Accept: 'application/json', ...extra };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  else if (isAuthSkipActive()) headers['X-Platform-Auth-Skip'] = AUTH_SKIP_HEADER_VALUE;
  if (body !== undefined && body !== null && !(body instanceof FormData)) {
    if (!headers['Content-Type']) headers['Content-Type'] = 'application/json';
  }
  return headers;
}

export async function apiFetch(path, options = {}) {
  const { params, timeoutMs = 30_000, signal: parentSignal, body, ...rest } = options;
  const url = apiUrl(path, params);
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const onParentAbort = () => controller.abort(parentSignal?.reason);
  if (parentSignal) {
    if (parentSignal.aborted) onParentAbort();
    else parentSignal.addEventListener('abort', onParentAbort, { once: true });
  }

  const init = {
    ...rest,
    signal: controller.signal,
    headers: buildHeaders(rest.headers, body),
  };
  if (body !== undefined) {
    init.body = body instanceof FormData || typeof body === 'string' ? body : JSON.stringify(body);
  }

  try {
    const response = await fetch(url, init);
    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    const data = isJson ? await response.json().catch(() => null) : null;
    if (!response.ok) {
      const detail = data?.detail ?? data?.message ?? response.statusText;
      const err = new Error(typeof detail === 'string' ? detail : `${response.status} ${response.statusText}`);
      err.status = response.status;
      err.data = data;
      throw err;
    }
    return data;
  } finally {
    window.clearTimeout(timeout);
    parentSignal?.removeEventListener?.('abort', onParentAbort);
  }
}

export async function apiGet(path, options = {}) {
  return apiFetch(path, { ...options, method: 'GET' });
}

export async function apiPost(path, options = {}) {
  return apiFetch(path, { ...options, method: 'POST' });
}

export async function apiPatch(path, options = {}) {
  return apiFetch(path, { ...options, method: 'PATCH' });
}

export async function apiPut(path, options = {}) {
  return apiFetch(path, { ...options, method: 'PUT' });
}

export async function apiDelete(path, options = {}) {
  return apiFetch(path, { ...options, method: 'DELETE' });
}
```

## 2.5 Utils & Helpers

### File: `app_skeleton/ui/react_frontend/src/utils/ordersBillingCategories.js`

```javascript
/**
 * Side-tab categories for Billing & ordering instructions (orders_billing twin).
 * Mirrors the Google Drive folder layout with clearer labels.
 */

import {
  collectSectionDocuments,
  groupDocumentsByCategory,
  findCategoryMeta,
} from './documentBrowserUtils.js';

/** Human-readable titles for every file in this section. */
export const BILLING_DISPLAY_TITLES = {
  'BIlling_and_delivery_information_FÄRKKILÄ.docx':
    'Billing & Delivery Information (Färkkilä Lab)',
  'Booking_the_seminar_room.docx': 'Seminar Room Booking Instructions',
  'Laskulomake FI EN 05072017.docx': 'University of Helsinki Invoice Form (FI/EN)',
  'USERNAMES_and_PASSWORDS_to_websites_Färkkilä lab.docx':
    'Vendor Usernames & Passwords',
  'HUS_money/HUS EVO money Anniina, 2022.docx':
    'HUS EVO Budget & Billing Contacts (2022)',
  'HUS_money/HUS Laskutusohje 2024-2026.docx': 'HUS Billing Instructions 2024–2026',
  'HUS_money/HUSLAB_order_form.xls': 'HUSLAB Order Form',
  'Shipments_FedEx_UPS_Färkkilä_lab/FedEx account info.docx': 'FedEx Account Information',
  'Shipments_FedEx_UPS_Färkkilä_lab/Air Waybills FedEx/FedEx Air waybill 3 11 2020NC Abcam NL return of abs.pdf':
    'FedEx Waybill — Abcam NL Antibody Return (Nov 2020)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Air Waybills FedEx/FedEx Air waybill 24 5 2021  DNA S052 to Maria Rossing Copenhagen.pdf':
    'FedEx Waybill — DNA S052 to Maria Rossing, Copenhagen (May 2021)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Air Waybills FedEx/FedEx Denmark Maria Rossing 28 4 2021NC.pdf':
    'FedEx Waybill — Maria Rossing, Denmark (Apr 2021)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Air Waybills FedEx/FedEx Myriad DNAs to Copenhagen 8 3 21NC.pdf':
    'FedEx Waybill — Myriad DNAs to Copenhagen (Mar 2021)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment of DNA samples to Copenhagen, same as for Myriad test, 8.3.2021NC/FF DNAs sent to Denmark same as Myriad March 2021.xlsx':
    'DNA Shipment List — Denmark / Myriad (Mar 2021)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/Shipment to US advices.docx':
    'Shipment to US — Instructions & Advice',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/USDA_Statement_Human non hazardous.doc':
    'USDA Statement — Human Non-Hazardous Samples',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/CI&USDA Bente HalvorsenEllen Lund Sagen070622.docx':
    'Commercial Invoice & USDA — Bente Halvorsen / Ellen Lund Sagen',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/CI&USDA from Tapio Tainola.doc':
    'Commercial Invoice & USDA — Tapio Tainola',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/ProForma Anton Popov ESRF Magasin 060622.doc':
    'Proforma Invoice — Anton Popov, ESRF Magasin',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/ProForma Nadezhda Zinovkina-November University 261119.doc':
    'Proforma Invoice — Nadezhda Zinovkina, November University',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/Contour-Cut-Printed-Fragile-Decal-Sign.png':
    'Fragile Shipping Label (Decal)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/RareCyte slides shipment USDA and Customs invoice, Anastasiya/Customs Invoice Slides to RareCyte Customs Invoice.doc':
    'Customs Invoice — RareCyte Slides Shipment',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/RareCyte slides shipment USDA and Customs invoice, Anastasiya/USDA Statement Slides to RareCyte.doc':
    'USDA Statement — RareCyte Slides Shipment',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/UPS from 1 2 2022.docx':
    'UPS Courier Service — Setup & Instructions (from Feb 2022)',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/image007.png': 'UPS Setup Screenshot 1',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/image008.png': 'UPS Setup Screenshot 2',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/image009.png': 'UPS Setup Screenshot 3',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/Air waybills UPS/18.8.2025_Tartu_SNParray_Matilda_4_IDS_FF_DNAs_UPS CampusShip _ UPS - Finland.pdf':
    'UPS Waybill — SNParray DNAs to Tartu, Matilda (Aug 2025)',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/Air waybills UPS/DNA_to_Tartu_Matilda_7_04_2025_AL_UPS CampusShip _ UPS - Finland.pdf':
    'UPS Waybill — DNA to Tartu, Matilda (Apr 2025)',
};

export function billingDocumentTitle(doc) {
  if (doc?.display_title) return doc.display_title;
  const path = (doc?.path || '').replace(/\\/g, '/');
  if (BILLING_DISPLAY_TITLES[path]) return BILLING_DISPLAY_TITLES[path];
  const fileName = path.split('/').pop() || '';
  return fileName.replace(/\.[^.]+$/, '').replace(/_/g, ' ').replace(/^BIlling/i, 'Billing');
}

export const BILLING_CATEGORY_GROUPS = [
  {
    id: 'billing',
    label: 'Billing & Finance',
    categories: [
      {
        id: 'general_reference',
        label: 'General Reference',
        description: 'Core billing addresses, delivery info, and university invoice forms.',
      },
      {
        id: 'hus_finance',
        label: 'HUS Finance & Billing',
        description: 'HUS billing instructions, EVO budgets, and HUSLAB order forms.',
      },
      {
        id: 'credentials',
        label: 'Credentials & Access',
        description: 'Vendor website logins and account credentials (sensitive).',
        sensitive: true,
      },
    ],
  },
  {
    id: 'logistics',
    label: 'Logistics & Shipping',
    categories: [
      {
        id: 'fedex',
        label: 'FedEx',
        description: 'FedEx account details and archived air waybills.',
      },
      {
        id: 'ups',
        label: 'UPS',
        description: 'UPS courier setup, screenshots, and air waybills.',
      },
      {
        id: 'dna_shipments',
        label: 'DNA Sample Shipments',
        description: 'International DNA shipments (Copenhagen, Myriad, Denmark).',
      },
      {
        id: 'us_customs',
        label: 'US Customs & Proforma',
        description: 'USDA statements, proforma invoices, and customs examples.',
      },
    ],
  },
  {
    id: 'other',
    label: 'Other',
    categories: [
      {
        id: 'other_admin',
        label: 'Admin & Facilities',
        description: 'Room booking and other administrative references.',
      },
    ],
  },
];

export const BILLING_CATEGORY_ORDER = BILLING_CATEGORY_GROUPS.flatMap((g) =>
  g.categories.map((c) => c.id)
);

export function categorizeBillingPath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/');
  const lower = p.toLowerCase();
  const fileName = p.split('/').pop().toLowerCase();

  if (lower.includes('usernames_and_passwords')) return 'credentials';
  if (p.startsWith('HUS_money/')) return 'hus_finance';
  // Filename carrier hint (e.g. UPS CampusShip PDF stored under FedEx folder)
  if (fileName.includes('ups') || fileName.includes('campusship')) return 'ups';
  if (fileName.includes('fedex') || lower.endsWith('fedex account info.docx')) return 'fedex';
  if (lower.includes('air waybills fedex')) return 'fedex';
  if (lower.includes('/ups/')) return 'ups';
  if (lower.includes('dna samples to copenhagen') || lower.includes('myriad')) {
    return 'dna_shipments';
  }
  if (
    lower.includes('shipment to us') ||
    lower.includes('rarecyte') ||
    lower.includes('usda') ||
    lower.includes('proforma')
  ) {
    return 'us_customs';
  }
  if (lower.includes('booking_the_seminar_room')) return 'other_admin';
  if (
    lower.includes('billing_and_delivery') ||
    lower.includes('laskulomake')
  ) {
    return 'general_reference';
  }
  return 'general_reference';
}

export function collectBillingDocuments(twin) {
  return collectSectionDocuments(twin, {
    categorizePath: categorizeBillingPath,
    documentTitle: billingDocumentTitle,
  });
}

export function groupBillingDocuments(docs) {
  return groupDocumentsByCategory(docs, BILLING_CATEGORY_ORDER);
}

export function findBillingCategoryMeta(categoryId) {
  return findCategoryMeta(BILLING_CATEGORY_GROUPS, categoryId);
}
```

---

# 3. Scripts (Python)

## 3.1 Database Ingestion

### File: `scripts/database/ingest_database.py`

```python
#!/usr/bin/env python3
import os
import csv
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parents[1]
DB_CONN = os.getenv("POSTGRES_CONN", "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai")

def main():
    print(f"Connecting to database at: {DB_CONN}")
    with psycopg.connect(DB_CONN) as conn:
        with conn.cursor() as cur:
            # 1. Ingest Projects
            projects = [
                ("SPACE", "Precision Oncology of Spatial Immune Escape Mechanisms in Ovarian Cancer", "TBD", "TBD", "HGSC", "Spatial immune escape in chemo-naive HGSC", "internal", "active"),
                ("EyeMT", "Immune escape multiomics integration", "TBD", "TBD", "HGSC", "tCyCIF + GeoMx + WES integration", "internal", "active"),
                ("KRAS", "KRAS Project Analysis", "TBD", "TBD", "HGSC", "Consolidated KRAS Spatial and thresholding analysis", "internal", "active")
            ]
            for code, name, lead, pi, focus, desc, sens, status in projects:
                cur.execute("""
                    INSERT INTO core.project (project_code, project_name, project_lead, principal_investigator, disease_focus, short_description, default_sensitivity, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::core.sensitivity_level, %s::core.record_status)
                    ON CONFLICT (project_code) DO UPDATE
                    SET project_name = EXCLUDED.project_name,
                        disease_focus = EXCLUDED.disease_focus,
                        short_description = EXCLUDED.short_description;
                """, (code, name, lead, pi, focus, desc, sens, status))
            print("Successfully registered projects.")

            # 2. Ingest Cohorts
            cohorts = [
                ("SPACE", "SPACE_COHORT", "SPACE Core Cohort"),
                ("EyeMT", "EyeMT_COHORT", "EyeMT Core Cohort"),
                ("KRAS", "KRAS_COHORT", "KRAS Core Cohort")
            ]
            for p_code, c_code, c_name in cohorts:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (p_code,))
                p_id = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO core.cohort (project_id, cohort_code, cohort_name, status)
                    VALUES (%s, %s, %s, 'active')
                    ON CONFLICT (project_id, cohort_code) DO NOTHING;
                """, (p_id, c_code, c_name))
            print("Successfully registered cohorts.")

            # 3. Ingest Synthetic Patients
            patients_csv = ROOT / "synthetic_data" / "synthetic_patients.csv"
            if patients_csv.exists():
                with open(patients_csv, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Map clinical info to metadata JSONB
                        metadata = {
                            "histology": row["histology"],
                            "hrd_status": row["hrd_status"],
                            "brca_status": row["brca_status"],
                            "platinum_response": row["platinum_response"],
                            "pfs_months": float(row["pfs_months"]),
                            "os_months": float(row["os_months"])
                        }
                        cur.execute("""
                            INSERT INTO core.patient (patient_code, disease_label, sensitivity_level, status, metadata)
                            VALUES (%s, %s, 'restricted', 'active', %s)
                            ON CONFLICT (patient_code) DO UPDATE
                            SET metadata = EXCLUDED.metadata;
                        """, (row["patient_code"], row["histology"], psycopg.types.json.Jsonb(metadata)))
                print("Successfully ingested synthetic patients.")

            # 4. Ingest Specimens & Samples
            samples_csv = ROOT / "synthetic_data" / "synthetic_samples.csv"
            if samples_csv.exists():
                with open(samples_csv, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        p_code = row["project_code"]
                        pat_code = row["patient_code"]
                        s_code = row["sample_code"]
                        site = row["site"]
                        modality = row["modality"]

                        # Get Project, Cohort and Patient IDs
                        cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (p_code,))
                        p_id = cur.fetchone()[0]

                        cur.execute("SELECT cohort_id FROM core.cohort WHERE project_id = %s;", (p_id,))
                        c_id = cur.fetchone()[0]

                        cur.execute("SELECT patient_id FROM core.patient WHERE patient_code = %s;", (pat_code,))
                        pat_id = cur.fetchone()[0]

                        # Insert Specimen (assume 1-to-1 with sample for synthetic data)
                        spec_code = f"SPEC_{s_code}"
                        cur.execute("""
                            INSERT INTO core.specimen (patient_id, specimen_code, anatomical_site, sensitivity_level)
                            VALUES (%s, %s, %s, 'restricted')
                            ON CONFLICT (specimen_code) DO NOTHING;
                        """, (pat_id, spec_code, site))

                        cur.execute("SELECT specimen_id FROM core.specimen WHERE specimen_code = %s;", (spec_code,))
                        spec_id = cur.fetchone()[0]

                        # Insert Sample
                        metadata = {"modality": modality}
                        cur.execute("""
                            INSERT INTO core.sample (patient_id, specimen_id, project_id, cohort_id, sample_code, sample_name, sample_type, anatomical_site, qc_status, sensitivity_level, status, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pass', 'restricted', 'active', %s)
                            ON CONFLICT (sample_code) DO UPDATE
                            SET metadata = EXCLUDED.metadata, qc_status = 'pass';
                        """, (pat_id, spec_id, p_id, c_id, s_code, s_code, modality, site, psycopg.types.json.Jsonb(metadata)))
                print("Successfully ingested synthetic samples.")

        conn.commit()
    print("Database seeding completed.")

if __name__ == "__main__":
    main()
```

## 3.2 Vector Database Setup

### File: `scripts/ingest/create_qdrant_collections.py`

```python
#!/usr/bin/env python3
from __future__ import annotations
import os
from pathlib import Path
import yaml
from qdrant_client import QdrantClient
from qdrant_client.http import models

ROOT = Path(__file__).resolve().parents[1]
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
```

## 3.3 Document Processing

### File: `scripts/ingest/ingest_documents_demo.py`

```python
#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import math
import os
import re
from pathlib import Path
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
COMPILED_SCRIPTS_DIR = Path("/Users/debashishdeb/Downloads/OMEIA-AI/projects/compiled_scripts")

def pseudo_semantic_embed(text: str, dim: int = 384) -> List[float]:
    """
    Zero-dependency term-frequency (bag-of-words) unit vectorizer.
    Yields cosine similarities corresponding to word overlap,
    making exact-word queries match documents containing those words.
    """
    vec = [0.0] * dim
    # Clean text and extract alphanumeric words
    words = re.findall(r'[a-zA-Z0-9_\-]+', text.lower())
    for w in words:
        # Simple stop words filtering
        if w in {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
                 'to', 'in', 'of', 'for', 'on', 'with', 'at', 'by', 'from', 'this',
                 'that', 'these', 'those', 'it', 'its', 'as', 'we', 'you', 'i', 'our'}:
            continue
        # Use SHA-256 to hash the word into an index
        h = int(hashlib.sha256(w.encode('utf-8')).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
        
    # Normalize to unit length
    norm = math.sqrt(sum(v*v for v in vec))
    if norm < 0.0001:
        # Fallback to deterministic hash of the entire text if empty
        h_all = hashlib.sha256(text.encode('utf-8')).digest()
        vec = [((h_all[i % len(h_all)] / 255.0) * 2 - 1) for i in range(dim)]
        norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v / norm for v in vec]

def chunk_markdown(filepath: Path) -> List[Dict[str, str]]:
    """Splits a markdown file into sections based on headers."""
    content = filepath.read_text(encoding='utf-8', errors='ignore')
    sections = []
    current_header = "Header"
    current_lines = []
    
    for line in content.splitlines():
        if line.startswith('#'):
            if current_lines:
                sections.append({
                    "header": current_header,
                    "text": "\n".join(current_lines).strip()
                })
            current_header = line.strip('# ')
            current_lines = [line]
        else:
            current_lines.append(line)
            
    if current_lines:
        sections.append({
            "header": current_header,
            "text": "\n".join(current_lines).strip()
        })
        
    return sections

def main():
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=qdrant_url)
    
    # --- 1. Ingest Documentation in doc_chunks ---
    doc_points = []
    print("Reading documentation files from docs/...")
    
    for doc_file in sorted(DOCS_DIR.glob("*.md")):
        print(f"  Processing {doc_file.name}")
        chunks = chunk_markdown(doc_file)
        for i, chunk in enumerate(chunks):
            title = f"{doc_file.name}: {chunk['header']}"
            text = chunk['text']
            if not text:
                continue
                
            point_id = hashlib.md5(f"doc_{doc_file.name}_{i}".encode('utf-8')).hexdigest()
            payload = {
                "schema_version": 1,
                "source_type": "documentation",
                "document_id": doc_file.name,
                "source_file_id": doc_file.name,
                "chunk_id": str(i),
                "title": title,
                "text_preview": text[:1000],
                "project_code": "SPACE", # Default scope
                "modality": ["documentation"],
                "sensitivity_level": "internal",
                "allowed_project_codes": ["SPACE", "EyeMT", "KRAS"],
                "contains_patient_level_data": False,
                "contains_direct_identifier": False,
                "embedding_model": "pseudo_semantic_bag_of_words",
                "embedding_dimension": 384,
                "created_at": "2026-06-02T12:00:00Z",
                "status": "active"
            }
            doc_points.append(models.PointStruct(
                id=point_id,
                vector={"text": pseudo_semantic_embed(text)},
                payload=payload
            ))
            
    if doc_points:
        client.upsert(collection_name="doc_chunks", points=doc_points)
        print(f"Upserted {len(doc_points)} points into doc_chunks.")

    # --- 2. Ingest Consolidated Script Files in script_chunks ---
    script_points = []
    # Map consolidated file names to project codes
    project_mapping = {
        "image_processing_scripts.md": "SPACE",
        "cefiira_scripts.md": "EyeMT",
        "kras_scripts.md": "KRAS",
        "geomx_processing_scripts.md": "EyeMT",
        "spacestat_scripts.md": "SPACE",
        "space_scripts.md": "SPACE",
        "cellcycle_scripts.md": "EyeMT",
        "tribus_scripts.md": "EyeMT",
        "eyemt_scripts.md": "EyeMT",
        "clinical_data_curation_scripts.md": "EyeMT",
        "finprove_scripts.md": "SPACE"
    }
    
    if COMPILED_SCRIPTS_DIR.exists():
        print("Reading compiled script files...")
        for script_file in sorted(COMPILED_SCRIPTS_DIR.glob("*.md")):
            proj_code = project_mapping.get(script_file.name, "SPACE")
            print(f"  Processing script file {script_file.name} for project {proj_code}")
            
            chunks = chunk_markdown(script_file)
            for i, chunk in enumerate(chunks):
                title = f"{script_file.name}: {chunk['header']}"
                text = chunk['text']
                if not text:
                    continue
                    
                # Determine language inside this chunk
                lang = "python"
                if "```bash" in text:
                    lang = "bash"
                elif "```r" in text:
                    lang = "r"
                
                point_id = hashlib.md5(f"script_{script_file.name}_{i}".encode('utf-8')).hexdigest()
                payload = {
                    "schema_version": 1,
                    "repo": script_file.name.replace("_scripts.md", ""),
                    "file_path": chunk['header'],
                    "language": lang,
                    "pipeline_stage": "analysis" if "analysis" in chunk['header'].lower() else "processing",
                    "project_code": proj_code,
                    "sensitivity_level": "internal",
                    "title": title,
                    "text_preview": text[:1000],
                    "created_at": "2026-06-02T12:00:00Z"
                }
                script_points.append(models.PointStruct(
                    id=point_id,
                    vector={"text": pseudo_semantic_embed(text)},
                    payload=payload
                ))
                
        if script_points:
            client.upsert(collection_name="script_chunks", points=script_points)
            print(f"Upserted {len(script_points)} points into script_chunks.")
            
    print("Qdrant document and script ingestion complete.")

if __name__ == "__main__":
    main()
```

---

# 4. Configuration

## 4.1 Docker Compose

### File: `configs/docker-compose.dev.yml`

```yaml
services:
  postgres:
    image: postgres:16
    container_name: farkki_ai_postgres
    environment:
      POSTGRES_USER: farkki
      POSTGRES_PASSWORD: farkki_dev_password
      POSTGRES_DB: farkki_ai
    ports:
      - "5432:5432"
    volumes:
      - farkki_pgdata:/var/lib/postgresql/data
      - ../sql:/docker-entrypoint-initdb.d:ro

  qdrant:
    image: qdrant/qdrant:latest
    container_name: farkki_ai_qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - farkki_qdrant:/qdrant/storage

  neo4j:
    image: neo4j:5
    container_name: farkki_ai_neo4j
    environment:
      NEO4J_AUTH: neo4j/farkki_dev_password
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - farkki_neo4j_data:/data
      - farkki_neo4j_logs:/logs

  minio:
    image: minio/minio:latest
    container_name: farkki_ai_minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: farkki
      MINIO_ROOT_PASSWORD: farkki_dev_password
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - farkki_minio:/data

volumes:
  farkki_pgdata:
  farkki_qdrant:
  farkki_neo4j_data:
  farkki_neo4j_logs:
  farkki_minio:
```

---

# 5. Database Schema

## 5.1 Core Schema

### File: `sql/010_core_schema.sql`

```sql
CREATE TABLE IF NOT EXISTS core.project (
  project_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_code text NOT NULL UNIQUE,
  project_name text NOT NULL,
  short_description text,
  long_description text,
  disease_focus text,
  principal_investigator text,
  project_lead text,
  start_date date,
  end_date date,
  default_sensitivity core.sensitivity_level NOT NULL DEFAULT 'internal',
  status core.record_status NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.cohort (
  cohort_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES core.project(project_id) ON DELETE CASCADE,
  cohort_code text NOT NULL,
  cohort_name text NOT NULL,
  cohort_description text,
  inclusion_criteria text,
  exclusion_criteria text,
  source_system text,
  status core.record_status NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_id, cohort_code)
);

CREATE TABLE IF NOT EXISTS core.patient (
  patient_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_code text NOT NULL UNIQUE,
  source_system text,
  diagnosis_year integer,
  birth_year_bin text,
  sex_at_birth_code text,
  disease_label text,
  sensitivity_level core.sensitivity_level NOT NULL DEFAULT 'restricted',
  status core.record_status NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.patient_cohort_membership (
  patient_id uuid REFERENCES core.patient(patient_id) ON DELETE CASCADE,
  cohort_id uuid REFERENCES core.cohort(cohort_id) ON DELETE CASCADE,
  membership_status text NOT NULL DEFAULT 'included',
  inclusion_notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(patient_id, cohort_id)
);

CREATE TABLE IF NOT EXISTS core.specimen (
  specimen_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id uuid NOT NULL REFERENCES core.patient(patient_id) ON DELETE CASCADE,
  specimen_code text NOT NULL UNIQUE,
  anatomical_site text,
  anatomical_site_detail text,
  collection_timepoint text,
  surgery_type text,
  treatment_context text,
  block_id text,
  section_id text,
  collection_year integer,
  sensitivity_level core.sensitivity_level NOT NULL DEFAULT 'restricted',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.sample (
  sample_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id uuid REFERENCES core.patient(patient_id) ON DELETE SET NULL,
  specimen_id uuid REFERENCES core.specimen(specimen_id) ON DELETE SET NULL,
  project_id uuid REFERENCES core.project(project_id) ON DELETE SET NULL,
  cohort_id uuid REFERENCES core.cohort(cohort_id) ON DELETE SET NULL,
  sample_code text NOT NULL UNIQUE,
  sample_name text,
  sample_type text,
  anatomical_site text,
  timepoint text,
  batch_code text,
  qc_status text DEFAULT 'unknown',
  sensitivity_level core.sensitivity_level NOT NULL DEFAULT 'restricted',
  status core.record_status NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.marker (
  marker_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name text NOT NULL UNIQUE,
  display_name text,
  marker_type text,
  gene_symbol text,
  protein_name text,
  description text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.marker_alias (
  marker_alias_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  marker_id uuid NOT NULL REFERENCES core.marker(marker_id) ON DELETE CASCADE,
  alias text NOT NULL,
  alias_type text,
  source text,
  UNIQUE(marker_id, alias)
);

CREATE TABLE IF NOT EXISTS core.cell_type (
  cell_type_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name text NOT NULL UNIQUE,
  display_name text,
  parent_cell_type_id uuid REFERENCES core.cell_type(cell_type_id),
  description text,
  created_at timestamptz NOT NULL DEFAULT now()
);
```

---

## Architecture Index

### Backend API Architecture
- **Entry Point**: `main.py` - FastAPI application setup with CORS, routers, and static file serving
- **API Routers**: 
  - `copilot.py` - AI copilot endpoints, billing instructions, LLM integration
  - `datapad.py` - Project file management, digital twin operations, document editing
- **Core Services**:
  - `llm_client.py` - Multi-provider LLM client (OpenAI, Groq, Ollama, etc.)
  - `qdrant_vectors.py` - Vector database operations and embeddings
  - `database_processor.py` - Lab database section processing and extraction

### Frontend React Architecture
- **Entry Points**: 
  - `main.jsx` - React root with providers (API, Locale, Theme)
  - `App.jsx` - Main application component with navigation and routing
- **Screens**:
  - `OrdersHubScreen.jsx` - Orders/billing/logistics hub with document blueprints
  - Other screens for dashboard, projects, bioinformatics, etc.
- **Components**:
  - `OrdersBillingBrowser.jsx` - Billing document browser with category filtering
  - `LabDocumentsBrowser.jsx` - Generic document browser with preview pane
- **API Client**: `client.js` - Shared API client with authentication and error handling
- **Utils**: `ordersBillingCategories.js` - Billing category definitions and path categorization

### Scripts Architecture
- **Database**: `ingest_database.py` - PostgreSQL seeding with projects, cohorts, patients, samples
- **Vector DB**: `create_qdrant_collections.py` - Qdrant collection setup with indexing
- **Documents**: `ingest_documents_demo.py` - Document chunking and vector embedding

### Configuration Architecture
- **Docker**: `docker-compose.dev.yml` - Development stack (PostgreSQL, Qdrant, Neo4j, MinIO)

### Database Schema Architecture
- **Core**: `010_core_schema.sql` - Projects, cohorts, patients, specimens, samples, markers, cell types

---

**End of Complete Code Collection**

*This document contains all source code from the OMEIA Digital Notepad project, organized by architectural layer for easy reference and navigation.*
