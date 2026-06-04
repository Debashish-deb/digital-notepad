"""Provider-routed LLM client for OMEIA.

Drop-in upgrade for the original LLMClient:
- deterministic mock mode for offline demos/tests
- bounded provider fallback without recursive state corruption
- safer logging and timeouts
- optional OpenAI-compatible chat providers
- stable local embeddings for Qdrant RAG
"""
from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from dataclasses import dataclass
from typing import Any, List

import requests
from openai import OpenAI

LOGGER = logging.getLogger(__name__)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "to", "in",
    "of", "for", "on", "with", "at", "by", "from", "this", "that", "these", "those",
    "it", "its", "as", "be", "can", "how", "what", "why", "when", "where", "which",
}


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""


class LLMClient:
    """Small OpenAI-compatible provider router used by the API."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
        self.model = os.getenv("LLM_MODEL", "mock-model").strip()
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.base_url = os.getenv("LLM_BASE_URL", "").strip()
        fallback_env = os.getenv("LLM_FALLBACK_PROVIDERS", "groq,openai,openrouter,together,ollama,mock")
        self.fallback_providers = [p.strip().lower() for p in fallback_env.split(",") if p.strip()]
        if "mock" not in self.fallback_providers:
            self.fallback_providers.append("mock")
        self.timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1400"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
        self.client: OpenAI | None = None
        self._init_client()

    def _config_for(self, provider: str) -> ProviderConfig:
        provider = (provider or "mock").lower()
        if provider == "openai":
            return ProviderConfig("openai", os.getenv("OPENAI_MODEL", self.model or "gpt-4o-mini"), os.getenv("OPENAI_API_KEY", self.api_key), "")
        if provider == "groq":
            return ProviderConfig("groq", os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"), os.getenv("GROQ_API_KEY", self.api_key), os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))
        if provider == "openrouter":
            return ProviderConfig("openrouter", os.getenv("OPENROUTER_MODEL", self.model or "openai/gpt-4o-mini"), os.getenv("OPENROUTER_API_KEY", self.api_key), os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
        if provider == "together":
            return ProviderConfig("together", os.getenv("TOGETHER_MODEL", self.model or "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"), os.getenv("TOGETHER_API_KEY", self.api_key), os.getenv("TOGETHER_BASE_URL", "https://api.together.xyz/v1"))
        if provider == "ollama":
            return ProviderConfig("ollama", os.getenv("OLLAMA_MODEL", "llama3"), "ollama", os.getenv("OLLAMA_BASE_URL", self.base_url or "http://localhost:11434/v1"))
        return ProviderConfig("mock", "mock-model", "", "")

    def _init_client(self):
        """Initialise the configured primary provider, falling back to mock if unavailable."""
        cfg = ProviderConfig(self.provider, self.model, self.api_key, self.base_url)
        if self.provider != "mock" and not (self.api_key or self.provider == "ollama"):
            cfg = self._config_for(self.provider)

        if cfg.provider == "mock" or (not cfg.api_key and cfg.provider != "ollama"):
            self.provider, self.model, self.api_key, self.base_url = "mock", "mock-model", "", ""
            self.client = None
            return

        self.provider, self.model, self.api_key, self.base_url = cfg.provider, cfg.model, cfg.api_key, cfg.base_url
        kwargs: dict[str, Any] = {
            "api_key": cfg.api_key,
            "timeout": self.timeout_seconds,
            "max_retries": 1,
        }
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        self.client = OpenAI(**kwargs)

    def _client_for(self, cfg: ProviderConfig) -> OpenAI | None:
        if cfg.provider == "mock" or (not cfg.api_key and cfg.provider != "ollama"):
            return None
        kwargs: dict[str, Any] = {"api_key": cfg.api_key, "timeout": self.timeout_seconds, "max_retries": 1}
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        return OpenAI(**kwargs)

    def healthCheck(self) -> bool:
        """Verify whether the current provider is responsive."""
        if self.provider == "mock":
            return True
        try:
            if self.provider == "ollama":
                base = (self.base_url or "http://localhost:11434/v1").replace("/v1", "")
                return requests.get(base, timeout=2).status_code < 500
            if self.client:
                self.client.models.list()
                return True
        except Exception as exc:
            LOGGER.debug("LLM health check failed for %s: %s", self.provider, exc)
        return False

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

    def generate(self, prompt: str, system_prompt: str) -> str:
        """Generate conversational text with automatic fallback routing."""
        providers = [self.provider] + [p for p in self.fallback_providers if p != self.provider]
        errors: list[str] = []

        for provider in providers:
            cfg = self._config_for(provider)
            if provider == self.provider and self.provider != "mock":
                cfg = ProviderConfig(self.provider, self.model, self.api_key, self.base_url)

            if cfg.provider != "mock" and not cfg.api_key and cfg.provider != "ollama":
                continue

            try:
                result = self._chat_once(cfg, prompt, system_prompt)
                if result:
                    self.provider, self.model, self.api_key, self.base_url = cfg.provider, cfg.model, cfg.api_key, cfg.base_url
                    self.client = self._client_for(cfg)
                    return result
            except Exception as exc:
                errors.append(f"{cfg.provider}: {type(exc).__name__}")
                LOGGER.warning("LLM provider %s failed: %s", cfg.provider, exc)

        fallback = self._mock_generate(prompt, system_prompt)
        if errors:
            fallback += "\n\n*Provider fallback note: " + "; ".join(errors[:4]) + ".*"
        return fallback

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

    def _mock_generate(self, prompt: str, system_prompt: str) -> str:
        """Dynamic offline synthesizer for local development and demos."""
        q_match = re.search(r"Question:\s*(.*)", prompt or "", re.DOTALL | re.IGNORECASE)
        question = q_match.group(1).strip() if q_match else "General query"
        lower_q = question.lower()

        def _count(label: str) -> int:
            m = re.search(rf"{re.escape(label)}:\s*(\d+)", prompt or "", re.I)
            return int(m.group(1)) if m else 0

        patients_cnt = _count("Patient total")
        samples_cnt = _count("Sample total")
        sources = self._extract_sources(prompt)

        if "napari" in lower_q and "macos" in lower_q:
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
                "The most likely issue is a display/Qt/OpenGL initialization problem. Try running Napari on a workstation, using X11 forwarding, "
                "or setting `QT_QPA_PLATFORM=offscreen` for non-interactive checks. Install missing XCB libraries on minimal Linux hosts.\n\n"
                + self._format_source_notes(sources, "opengl")
            )

        if any(k in lower_q for k in ("count", "sample", "patient")):
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

        bullets = []
        query_terms = {w for w in re.findall(r"[a-zA-Z0-9_\-]+", lower_q) if w not in _STOPWORDS and len(w) > 2}
        for source in sources[:5]:
            content = source["content"]
            sentences = re.split(r"(?<=[.!?])\s+", content)
            selected = [s.strip() for s in sentences if any(term in s.lower() for term in query_terms)]
            excerpt = " ".join(selected[:2]) or content[:360]
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
        for s in sources:
            if keyword and keyword not in (s["title"] + " " + s["content"]).lower():
                continue
            lines.append(f"- [{s['index']}] {s['title']}: {s['content'][:220]}...")
        return "\n".join(lines) if len(lines) > 1 else ""

    def embed(self, text: str, dim: int = 384) -> List[float]:
        """Generate a stable L2-normalized hashed embedding for offline RAG.

        This intentionally avoids external calls by default so privacy-sensitive
        queries can still retrieve local Qdrant documentation.
        """
        dim = max(32, min(int(dim or 384), 4096))
        vec = [0.0] * dim
        tokens = re.findall(r"[a-zA-Z0-9_\-]+", (text or "").lower())

        for token in tokens:
            if token in _STOPWORDS:
                continue
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            idx = int.from_bytes(digest[:4], "big") % dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + min(len(token), 24) / 24.0
            vec[idx] += sign * weight

            # Add lightweight character n-gram signal for scientific terms.
            if len(token) >= 5:
                for i in range(min(len(token) - 2, 8)):
                    gram = token[i:i + 3]
                    gd = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
                    vec[int.from_bytes(gd[:4], "big") % dim] += 0.25

        norm = math.sqrt(sum(v * v for v in vec))
        if norm < 1e-9:
            seed = hashlib.blake2b((text or "empty").encode("utf-8"), digest_size=32).digest()
            vec = [((seed[i % len(seed)] / 255.0) * 2.0 - 1.0) for i in range(dim)]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
