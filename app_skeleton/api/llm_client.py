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
from typing import Any, Iterator, List

try:
    import requests
except Exception:  # pragma: no cover - dependency availability is environment-specific.
    requests = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - dependency availability is environment-specific.
    OpenAI = None  # type: ignore[assignment]

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

    _KNOWN_PROVIDERS = {"mock", "openai", "groq", "openrouter", "together", "ollama", "deepseek", "gemini"}

    def __init__(self):
        self.provider = _env("LLM_PROVIDER", "mock").lower() or "mock"
        if self.provider not in self._KNOWN_PROVIDERS:
            LOGGER.warning("Unknown LLM_PROVIDER=%s; falling back to mock", self.provider)
            self.provider = "mock"

        self.model = _env("LLM_MODEL", "mock-model") or "mock-model"
        self.api_key = _env("LLM_API_KEY", "")
        self.base_url = _env("LLM_BASE_URL", "")
        fallback_env = _env("LLM_FALLBACK_PROVIDERS", "gemini,groq,openai,openrouter,together,deepseek,ollama,mock")
        self.fallback_providers = self._normalize_provider_list(fallback_env)
        if "mock" not in self.fallback_providers:
            self.fallback_providers.append("mock")

        if self.provider == "gemini":
            if not self.api_key:
                self.api_key = _env("GEMINI_API_KEY", "")
            if not self.model or self.model == "mock-model":
                self.model = _env("GEMINI_MODEL", "gemini-2.0-flash")
            if not self.base_url:
                self.base_url = _env(
                    "GEMINI_BASE_URL",
                    "https://generativelanguage.googleapis.com/v1beta/openai/",
                )

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
        if provider == "openrouter":
            headers = {}
            site_url = _env("OPENROUTER_SITE_URL", "")
            app_name = _env("OPENROUTER_APP_NAME", "OMEIA")
            if site_url:
                headers["HTTP-Referer"] = site_url
            if app_name:
                headers["X-Title"] = app_name
            return ProviderConfig(
                "openrouter",
                _env("OPENROUTER_MODEL", self.model if self.provider == "openrouter" else "openai/gpt-4o-mini"),
                _env("OPENROUTER_API_KEY", self.api_key if self.provider == "openrouter" else ""),
                _env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                headers or None,
            )
        if provider == "together":
            return ProviderConfig(
                "together",
                _env("TOGETHER_MODEL", self.model if self.provider == "together" else "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
                _env("TOGETHER_API_KEY", self.api_key if self.provider == "together" else ""),
                _env("TOGETHER_BASE_URL", "https://api.together.xyz/v1"),
            )
        if provider == "deepseek":
            return ProviderConfig(
                "deepseek",
                _env("DEEPSEEK_MODEL", self.model if self.provider == "deepseek" else "deepseek-chat"),
                _env("DEEPSEEK_API_KEY", self.api_key if self.provider == "deepseek" else ""),
                _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            )
        if provider == "ollama":
            return ProviderConfig(
                "ollama",
                _env("OLLAMA_MODEL", self.model if self.provider == "ollama" else "llama3"),
                "ollama",
                _env("OLLAMA_BASE_URL", self.base_url or "http://localhost:11434/v1"),
            )
        if provider == "gemini":
            return ProviderConfig(
                "gemini",
                _env("GEMINI_MODEL", self.model if self.provider == "gemini" else "gemini-2.0-flash"),
                _env("GEMINI_API_KEY", self.api_key if self.provider == "gemini" else ""),
                _env(
                    "GEMINI_BASE_URL",
                    "https://generativelanguage.googleapis.com/v1beta/openai/",
                ),
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

    # PEP-8 alias for new code; old routers may still use healthCheck().
    def health_check(self) -> bool:
        return self.healthCheck()

    def _chat_once(self, cfg: ProviderConfig, prompt: str, system_prompt: str) -> str:
        client = self._client_for(cfg)
        if client is None:
            return self._mock_generate(prompt, system_prompt)

        response = client.chat.completions.create(
            model=cfg.model,
            messages=[
                {"role": "system", "content": system_prompt or "You are a helpful research copilot."},
                {"role": "user", "content": prompt or ""},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        content = response.choices[0].message.content
        return (content or "").strip()

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

    def _stream_once(self, cfg: ProviderConfig, prompt: str, system_prompt: str) -> Iterator[str]:
        client = self._client_for(cfg)
        if client is None:
            yield self._mock_generate(prompt, system_prompt)
            return

        stream = client.chat.completions.create(
            model=cfg.model,
            messages=[
                {"role": "system", "content": system_prompt or "You are a helpful research copilot."},
                {"role": "user", "content": prompt or ""},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    def stream_generate(self, prompt: str, system_prompt: str = "") -> Iterator[str]:
        """Stream conversational text deltas with the same fallback routing as generate()."""
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
                emitted = False
                for delta in self._stream_once(cfg, prompt, system_prompt):
                    emitted = True
                    yield delta
                if emitted:
                    self.provider, self.model, self.api_key, self.base_url = cfg.provider, cfg.model, cfg.api_key, cfg.base_url
                    self.client = self._client_for(cfg)
                    self.last_provider_errors = errors
                    return
            except Exception as exc:
                errors.append(f"{cfg.provider}: {type(exc).__name__}")
                LOGGER.warning("LLM stream provider %s failed: %s", cfg.provider, exc)

        self.last_provider_errors = errors
        fallback = self._mock_generate(prompt, system_prompt)
        if errors:
            fallback += "\n\n*Provider fallback note: " + "; ".join(errors[:4]) + ".*"
        yield fallback

    def _extract_sources(self, prompt: str) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []
        pattern = re.compile(r"\[(\d+)\] Source:\s*(.*?)\n(.*?)(?=\n\[\d+\] Source:|\n\nQuestion:|\Z)", re.DOTALL)
        for match in pattern.finditer(prompt or ""):
            sources.append({
                "index": match.group(1),
                "title": match.group(2).strip(),
                "content": match.group(3).strip(),
            })
        return sources

    @staticmethod
    def _extract_database_count(prompt: str, label: str) -> int:
        match = re.search(rf"{re.escape(label)}:\s*(\d+)", prompt or "", re.I)
        return int(match.group(1)) if match else 0

    def _mock_generate(self, prompt: str, system_prompt: str = "") -> str:
        """Dynamic offline synthesizer for local development, demos, and CI."""
        q_match = re.search(r"Question:\s*(.*)", prompt or "", re.DOTALL | re.IGNORECASE)
        question = q_match.group(1).strip() if q_match else "General query"
        lower_q = question.lower()
        patients_cnt = self._extract_database_count(prompt, "Patient total")
        samples_cnt = self._extract_database_count(prompt, "Sample total")
        sources = self._extract_sources(prompt)

        if "napari" in lower_q and any(os_word in lower_q for os_word in ("macos", "mac", "apple")):
            return (
                "### macOS Napari installation\n\n"
                "Use a native Miniforge/Mamba environment for Qt and OpenGL stability on Apple Silicon.\n\n"
                "```bash\n"
                "curl -L -O \"https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh\"\n"
                "bash Miniforge3-MacOSX-arm64.sh -b\n"
                "source ~/miniforge3/bin/activate\n"
                "mamba create -n napari_env python=3.10 napari pyqt -c conda-forge -y\n"
                "conda activate napari_env\n"
                "napari --info\n"
                "```\n\n"
                + self._format_source_notes(sources, "napari")
            )

        if "cylinter" in lower_q and "linux" in lower_q:
            return (
                "### Cylinter Linux installation\n\n"
                "```bash\n"
                "mamba create -n cylinter_env python=3.9 openjdk -c conda-forge -y\n"
                "conda activate cylinter_env\n"
                "python -m pip install --upgrade pip wheel setuptools\n"
                "python -m pip install cylinter==0.1.5\n"
                "cylinter --help\n"
                "```\n\n"
                + self._format_source_notes(sources, "cylinter")
            )

        if any(k in lower_q for k in ("opengl", "qt platform plugin", "crash")):
            return (
                "### Rendering/Qt diagnostic\n\n"
                "The most likely issue is a display/Qt/OpenGL initialization problem. Try running Napari on a workstation, "
                "using X11 forwarding, or setting `QT_QPA_PLATFORM=offscreen` for non-interactive checks. Install missing XCB libraries on minimal Linux hosts.\n\n"
                + self._format_source_notes(sources, "opengl")
            )

        if any(k in lower_q for k in ("count", "sample", "patient", "how many")):
            return (
                "### Registry metadata summary\n\n"
                f"- Total patients: **{patients_cnt}**\n"
                f"- Total samples: **{samples_cnt}**\n\n"
                "These values come from the structured database-count block supplied to the model. No patient identifiers are required for this summary.\n\n"
                + self._format_source_notes(sources)
            )

        if not sources:
            return (
                "### OMEIA copilot synthesis\n\n"
                "No matching document chunks were retrieved for this query. The structured database context is still available, "
                f"with {patients_cnt} patients and {samples_cnt} samples in the active scope."
            )

        query_terms = {
            word for word in _TOKEN_RE.findall(lower_q)
            if word not in _STOPWORDS and len(word) > 2
        }
        bullets: list[str] = []
        for source in sources[:6]:
            content = source["content"]
            sentences = re.split(r"(?<=[.!?])\s+", content)
            selected = [s.strip() for s in sentences if any(term in s.lower() for term in query_terms)]
            excerpt = " ".join(selected[:2]) or content[:420]
            bullets.append(f"- **[{source['index']}] {source['title']}** — {excerpt}")

        return (
            "### OMEIA copilot synthesis\n\n"
            f"Question: *{question}*\n\n"
            + "\n".join(bullets)
            + f"\n\n*System context: {patients_cnt} patients and {samples_cnt} samples in the active scope.*"
        )

    def _format_source_notes(self, sources: list[dict[str, str]], keyword: str | None = None) -> str:
        if not sources:
            return ""
        lines = ["**References retrieved:**"]
        for source in sources:
            haystack = (source["title"] + " " + source["content"]).lower()
            if keyword and keyword.lower() not in haystack:
                continue
            excerpt = source["content"][:240].replace("\n", " ")
            lines.append(f"- [{source['index']}] {source['title']}: {excerpt}...")
        return "\n".join(lines) if len(lines) > 1 else ""

    def embed(self, text: str, dim: int = 384) -> List[float]:
        """Generate a stable L2-normalized hashed embedding for offline RAG.

        This intentionally avoids external calls by default so privacy-sensitive
        queries can still retrieve local Qdrant documentation. It is deterministic
        across processes and suitable for local/private indexing demos.
        """
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

        # Add weak document-level features so extremely short scientific strings still separate.
        for gram in self._char_ngrams((text or "").lower(), n=4, limit=64):
            gd = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
            vec[int.from_bytes(gd[:4], "big") % dim] += 0.05

        norm = math.sqrt(sum(v * v for v in vec))
        if norm < 1e-9:
            seed = hashlib.blake2b((text or "empty").encode("utf-8"), digest_size=32).digest()
            vec = [((seed[i % len(seed)] / 255.0) * 2.0 - 1.0) for i in range(dim)]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    @staticmethod
    def _char_ngrams(text: str, *, n: int = 4, limit: int = 64) -> list[str]:
        compact = re.sub(r"\s+", " ", text.strip())
        if len(compact) < n:
            return []
        return [compact[i:i + n] for i in range(min(len(compact) - n + 1, limit))]

    def embed_many(self, texts: list[str], dim: int = 384) -> list[list[float]]:
        return [self.embed(text, dim=dim) for text in texts]

    def public_status(self) -> dict[str, Any]:
        """Return safe status metadata for health endpoints without exposing secrets."""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url_configured": bool(self.base_url),
            "api_key_configured": bool(self.api_key and self.provider not in {"mock", "ollama"}),
            "fallback_providers": [p for p in self.fallback_providers if p != "mock"] + ["mock"],
            "healthy": self.healthCheck(),
            "last_provider_errors": list(self.last_provider_errors[-4:]),
        }
