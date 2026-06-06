"""Production Docker service connection layer for OMEIA.

Features:
- Config-driven service registry (Ollama, Qdrant, Postgres)
- Startup probes + periodic health checks
- Exponential backoff reconnect
- Circuit breaker (closed / open / half-open)
- Optional lazy ``docker compose up -d <service>`` (dev-friendly)
- Audit logging for Docker LLM invocations
- Input sanitization before forwarding to local LLM containers
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_NULL_BYTE_RE = re.compile(r"\x00")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MAX_LLM_PROMPT_CHARS = 120_000


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    return _env(name, "true" if default else "false").lower() in ("1", "true", "yes", "on")


def _bounded_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(low, min(parsed, high))


def _bounded_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    return max(low, min(parsed, high))


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    compose_service: str
    base_url: str
    health_path: str = "/"
    health_method: str = "GET"
    bearer_token: str = ""
    startup_timeout_sec: float = 120.0
    critical: bool = False


@dataclass
class ServiceHealth:
    name: str
    healthy: bool
    latency_ms: float | None = None
    circuit: CircuitState = CircuitState.CLOSED
    last_error: str = ""
    auto_started: bool = False
    detail: dict[str, Any] = field(default_factory=dict)


class DockerServiceError(RuntimeError):
    """Structured upstream error for Docker service connectivity."""

    def __init__(self, service: str, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.service = service
        self.retryable = retryable


class DockerServiceClient:
    """Registry + health orchestration for compose-backed services."""

    def __init__(self) -> None:
        # DOCKER_LOCAL=false → Mac thin client: probe remote URLs only, never run compose.
        self.local_docker = _env_bool("DOCKER_LOCAL", True)
        self.auto_start_enabled = self.local_docker and _env_bool("DOCKER_AUTO_START", True)
        self.watch_unhealthy = self.local_docker and _env_bool("DOCKER_WATCH_UNHEALTHY", False)
        self.compose_file = _env("DOCKER_COMPOSE_FILE", "docker-compose.yml")
        self.project_root = Path(_env("OMEIA_REPO_ROOT", str(_REPO_ROOT)))
        self.health_interval_sec = _bounded_float(_env("DOCKER_HEALTH_INTERVAL_SEC", "30"), 30.0, 5.0, 600.0)
        self.failure_threshold = _bounded_int(_env("DOCKER_CIRCUIT_FAILURE_THRESHOLD", "5"), 5, 2, 20)
        self.recovery_timeout_sec = _bounded_float(_env("DOCKER_CIRCUIT_RECOVERY_SEC", "30"), 30.0, 5.0, 300.0)
        self.max_backoff_sec = _bounded_float(_env("DOCKER_MAX_BACKOFF_SEC", "60"), 60.0, 5.0, 300.0)
        self._registry = self._build_registry()
        self._circuits: dict[str, CircuitState] = {s.name: CircuitState.CLOSED for s in self._registry}
        self._failure_counts: dict[str, int] = {s.name: 0 for s in self._registry}
        self._opened_at: dict[str, float] = {}
        self._last_health: dict[str, ServiceHealth] = {}
        self._lock = threading.RLock()
        self._watcher_stop = threading.Event()
        self._watcher_thread: threading.Thread | None = None

    def _build_registry(self) -> list[ServiceSpec]:
        ollama_token = _env("OLLAMA_INTERNAL_TOKEN", _env("OLLAMA_PROXY_TOKEN", ""))
        ollama_base = _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        if ollama_base.endswith("/v1"):
            ollama_base = ollama_base[:-3]
        qdrant_url = _env("QDRANT_URL", "http://127.0.0.1:6333").rstrip("/")
        biomodels_gateway = _env("BIOMEDICAL_MODELS_GATEWAY_URL", "http://127.0.0.1:8100").rstrip("/")
        biomodels_embeddings = _env("BIOMEDICAL_EMBEDDINGS_URL", "http://127.0.0.1:8101").rstrip("/")
        specs = [
            ServiceSpec(
                name="ollama",
                compose_service="ollama",
                base_url=ollama_base,
                health_path="/",
                bearer_token=ollama_token,
                startup_timeout_sec=_bounded_float(_env("OLLAMA_STARTUP_TIMEOUT_SEC", "120"), 120.0, 20.0, 600.0),
                critical=_env("LLM_PROVIDER", "mock").lower() == "ollama"
                or _env("CHAT_LLM_PROVIDER", "").lower() == "ollama",
            ),
            ServiceSpec(
                name="ollama-proxy",
                compose_service="ollama-proxy",
                base_url=ollama_base,
                health_path="/",
                bearer_token=ollama_token,
                startup_timeout_sec=60.0,
                critical=False,
            ),
            ServiceSpec(
                name="qdrant",
                compose_service="qdrant",
                base_url=qdrant_url,
                health_path="/healthz",
                bearer_token=_env("QDRANT_API_KEY", ""),
                startup_timeout_sec=60.0,
                critical=False,
            ),
            ServiceSpec(
                name="postgres",
                compose_service="postgres",
                base_url="",
                health_path="",
                startup_timeout_sec=60.0,
                critical=True,
            ),
            ServiceSpec(
                name="biomedical-gateway",
                compose_service="biomedical-gateway",
                base_url=biomodels_gateway,
                health_path="/health",
                startup_timeout_sec=120.0,
                critical=False,
            ),
            ServiceSpec(
                name="biomedical-embeddings",
                compose_service="biomedical-embeddings",
                base_url=biomodels_embeddings,
                health_path="/health",
                startup_timeout_sec=180.0,
                critical=False,
            ),
        ]
        if _env_bool("BIOMODELS_ENABLE_REGISTRY", False):
            specs.extend([
                ServiceSpec(
                    name="biomedical-biogpt",
                    compose_service="biomedical-biogpt",
                    base_url=_env("BIOMEDICAL_BIOGPT_URL", "http://127.0.0.1:8102").rstrip("/"),
                    health_path="/health",
                    startup_timeout_sec=300.0,
                    critical=False,
                ),
                ServiceSpec(
                    name="biomedical-txgemma",
                    compose_service="biomedical-txgemma",
                    base_url=_env("BIOMEDICAL_TXGEMMA_URL", "http://127.0.0.1:8103").rstrip("/"),
                    health_path="/health",
                    startup_timeout_sec=300.0,
                    critical=False,
                ),
            ])
        return specs

    def get_spec(self, name: str) -> ServiceSpec | None:
        for spec in self._registry:
            if spec.name == name:
                return spec
        return None

    def ollama_openai_config(self) -> dict[str, str]:
        """Resolve Ollama OpenAI-compatible endpoint + auth for llm_client."""
        spec = self.get_spec("ollama") or self.get_spec("ollama-proxy")
        if spec is None:
            base = _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
            token = _env("OLLAMA_INTERNAL_TOKEN", "")
            return {"base_url": base, "api_key": token or "ollama", "bearer_token": token}
        base_v1 = spec.base_url.rstrip("/") + "/v1"
        token = spec.bearer_token
        return {
            "base_url": base_v1,
            "api_key": token or "ollama",
            "bearer_token": token,
        }

    def sanitize_llm_text(self, text: str, *, label: str = "prompt") -> str:
        """Strip dangerous control chars and cap size before Docker LLM forwarding."""
        cleaned = _NULL_BYTE_RE.sub("", str(text or ""))
        cleaned = _CONTROL_CHAR_RE.sub("", cleaned)
        if len(cleaned) > _MAX_LLM_PROMPT_CHARS:
            LOGGER.warning(
                "Truncating %s from %s to %s chars before Ollama forward",
                label,
                len(cleaned),
                _MAX_LLM_PROMPT_CHARS,
            )
            cleaned = cleaned[:_MAX_LLM_PROMPT_CHARS]
        return cleaned

    def audit_llm_invocation(
        self,
        *,
        model: str,
        provider: str = "ollama",
        latency_ms: float | None = None,
        success: bool = True,
        error: str = "",
        user_hint: str = "",
        prompt_chars: int = 0,
    ) -> None:
        LOGGER.info(
            "docker_llm_audit provider=%s model=%s success=%s latency_ms=%s user=%s prompt_chars=%s error=%s",
            provider,
            model,
            success,
            round(latency_ms or 0.0, 1),
            user_hint or "unknown",
            prompt_chars,
            (error or "")[:200],
        )

    def _circuit_allows(self, name: str) -> bool:
        state = self._circuits.get(name, CircuitState.CLOSED)
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.OPEN:
            opened = self._opened_at.get(name, 0.0)
            if time.monotonic() - opened >= self.recovery_timeout_sec:
                self._circuits[name] = CircuitState.HALF_OPEN
                return True
            return False
        return True  # half-open: single probe

    def _record_success(self, name: str) -> None:
        self._failure_counts[name] = 0
        self._circuits[name] = CircuitState.CLOSED

    def _record_failure(self, name: str) -> None:
        count = self._failure_counts.get(name, 0) + 1
        self._failure_counts[name] = count
        if count >= self.failure_threshold:
            self._circuits[name] = CircuitState.OPEN
            self._opened_at[name] = time.monotonic()
            LOGGER.warning("Circuit OPEN for docker service %s after %s failures", name, count)

    def _auth_headers(self, spec: ServiceSpec) -> dict[str, str]:
        if spec.bearer_token:
            return {"Authorization": f"Bearer {spec.bearer_token}"}
        return {}

    def _http_probe(self, spec: ServiceSpec) -> tuple[bool, float, str]:
        if requests is None:
            return False, 0.0, "requests_unavailable"
        if not spec.base_url:
            return False, 0.0, "no_http_endpoint"
        url = spec.base_url.rstrip("/") + spec.health_path
        started = time.monotonic()
        try:
            response = requests.request(
                spec.health_method,
                url,
                headers=self._auth_headers(spec),
                timeout=_bounded_float(_env("DOCKER_HEALTH_TIMEOUT_SEC", "5"), 5.0, 1.0, 30.0),
            )
            latency = (time.monotonic() - started) * 1000.0
            if response.status_code < 500:
                return True, latency, ""
            return False, latency, f"http_{response.status_code}"
        except Exception as exc:
            latency = (time.monotonic() - started) * 1000.0
            return False, latency, type(exc).__name__

    def _postgres_probe(self) -> tuple[bool, float, str]:
        started = time.monotonic()
        try:
            import psycopg

            conn_str = _env("POSTGRES_CONN", "")
            if not conn_str:
                host = _env("POSTGRES_HOST", "localhost")
                port = _env("POSTGRES_PORT", "5432")
                db = _env("POSTGRES_DB", "farkki_ai")
                user = _env("POSTGRES_USER", "farkki")
                password = _env("POSTGRES_PASSWORD", "farkki_dev_password")
                conn_str = f"postgresql://{user}:{password}@{host}:{port}/{db}"
            with psycopg.connect(conn_str, connect_timeout=5):
                pass
            latency = (time.monotonic() - started) * 1000.0
            return True, latency, ""
        except Exception as exc:
            latency = (time.monotonic() - started) * 1000.0
            return False, latency, type(exc).__name__

    def probe(self, name: str) -> ServiceHealth:
        spec = self.get_spec(name)
        if spec is None:
            return ServiceHealth(name=name, healthy=False, last_error="unknown_service")

        if not self._circuit_allows(name):
            return ServiceHealth(
                name=name,
                healthy=False,
                circuit=self._circuits.get(name, CircuitState.OPEN),
                last_error="circuit_open",
            )

        if name == "postgres":
            ok, latency, err = self._postgres_probe()
        else:
            ok, latency, err = self._http_probe(spec)

        if ok:
            self._record_success(name)
            health = ServiceHealth(
                name=name,
                healthy=True,
                latency_ms=latency,
                circuit=CircuitState.CLOSED,
            )
        else:
            self._record_failure(name)
            health = ServiceHealth(
                name=name,
                healthy=False,
                latency_ms=latency,
                circuit=self._circuits.get(name, CircuitState.CLOSED),
                last_error=err,
            )
        with self._lock:
            self._last_health[name] = health
        return health

    def _compose_up(self, compose_service: str) -> bool:
        if not self.local_docker or not self.auto_start_enabled:
            return False
        compose_path = self.project_root / self.compose_file
        if not compose_path.exists():
            LOGGER.debug("Compose file missing: %s", compose_path)
            return False
        try:
            LOGGER.info("Auto-starting docker compose service: %s", compose_service)
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_path), "up", "-d", compose_service],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            if result.returncode != 0:
                LOGGER.warning(
                    "docker compose up failed for %s: %s",
                    compose_service,
                    (result.stderr or result.stdout or "")[:400],
                )
                return False
            return True
        except Exception as exc:
            LOGGER.warning("docker compose up error for %s: %s", compose_service, exc)
            return False

    def ensure_healthy(self, name: str, *, allow_auto_start: bool | None = None) -> ServiceHealth:
        """Probe service; optionally auto-start compose service with exponential backoff."""
        allow_start = self.auto_start_enabled if allow_auto_start is None else allow_auto_start
        spec = self.get_spec(name)
        if spec is None:
            return ServiceHealth(name=name, healthy=False, last_error="unknown_service")

        health = self.probe(name)
        if health.healthy:
            return health

        if not allow_start:
            return health

        # Also start proxy when ollama is requested
        services_to_start = [spec.compose_service]
        if name == "ollama":
            proxy = self.get_spec("ollama-proxy")
            if proxy:
                services_to_start.append(proxy.compose_service)

        backoff = 1.0
        deadline = time.monotonic() + spec.startup_timeout_sec
        auto_started = False
        while time.monotonic() < deadline:
            for svc in services_to_start:
                if self._compose_up(svc):
                    auto_started = True
            time.sleep(min(backoff, self.max_backoff_sec))
            backoff = min(backoff * 2, self.max_backoff_sec)
            health = self.probe(name)
            if health.healthy:
                health.auto_started = auto_started
                return health

        health.auto_started = auto_started
        return health

    def bootstrap(self, *, names: list[str] | None = None) -> dict[str, Any]:
        """Startup verification for API lifespan / start.sh."""
        targets = names or ["postgres", "qdrant", "ollama-proxy", "ollama"]
        summary: dict[str, Any] = {
            "local_docker": self.local_docker,
            "auto_start": self.auto_start_enabled,
            "watch_unhealthy": self.watch_unhealthy,
            "services": {},
        }
        for name in targets:
            spec = self.get_spec(name)
            if spec is None:
                continue
            if name == "ollama" and _env("LLM_PROVIDER", "").lower() not in ("ollama", "") and _env(
                "CHAT_LLM_PROVIDER", ""
            ).lower() not in ("ollama", ""):
                # Skip heavy Ollama wait unless configured as LLM provider
                health = self.probe(name)
            else:
                health = self.ensure_healthy(name)
            summary["services"][name] = {
                "healthy": health.healthy,
                "latency_ms": health.latency_ms,
                "circuit": health.circuit.value,
                "auto_started": health.auto_started,
                "last_error": health.last_error,
                "critical": bool(spec.critical),
            }
        summary["all_critical_healthy"] = all(
            entry.get("healthy")
            for svc_name, entry in summary["services"].items()
            if (self.get_spec(svc_name) or ServiceSpec("", "", "")).critical
        )
        return summary

    def public_status(self) -> dict[str, Any]:
        with self._lock:
            services = {
                name: {
                    "healthy": h.healthy,
                    "latency_ms": h.latency_ms,
                    "circuit": h.circuit.value,
                    "last_error": h.last_error,
                }
                for name, h in self._last_health.items()
            }
        return {
            "local_docker": self.local_docker,
            "auto_start_enabled": self.auto_start_enabled,
            "watch_unhealthy": self.watch_unhealthy,
            "compose_file": self.compose_file,
            "services": services,
            "ollama": {
                "base_url_configured": bool(_env("OLLAMA_BASE_URL", "")),
                "token_configured": bool(_env("OLLAMA_INTERNAL_TOKEN", "")),
            },
        }

    def _watcher_loop(self) -> None:
        while not self._watcher_stop.is_set():
            for spec in self._registry:
                if spec.name == "ollama-proxy":
                    continue
                health = self.probe(spec.name)
                if not health.healthy and self.watch_unhealthy:
                    LOGGER.warning("Watcher restarting unhealthy service: %s", spec.compose_service)
                    self._compose_up(spec.compose_service)
            self._watcher_stop.wait(self.health_interval_sec)

    def start_background_watcher(self) -> None:
        if not self.watch_unhealthy or self._watcher_thread:
            return
        self._watcher_thread = threading.Thread(
            target=self._watcher_loop,
            name="docker-service-watcher",
            daemon=True,
        )
        self._watcher_thread.start()
        LOGGER.info("Docker unhealthy-service watcher started (interval=%ss)", self.health_interval_sec)

    def stop_background_watcher(self) -> None:
        self._watcher_stop.set()
        if self._watcher_thread:
            self._watcher_thread.join(timeout=2.0)
            self._watcher_thread = None


# Module singleton — imported by llm_client and API lifespan.
docker_services = DockerServiceClient()
