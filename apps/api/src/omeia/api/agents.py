"""OMEIA copilot specialist agents.

Production-grade drop-in upgrade.

Compatibility promises:
- Keeps the public classes used by existing routers: PrivacyGuardrailAgent,
  RAGAgent, InstallationSpecialist, ScriptGeneratorAgent, LumiHpcAgent,
  TroubleshootingAgent, ImagePipelineSpecialist, ClinicalSpatialSpecialist.
- Keeps method names and return shapes compatible with the previous version.
- Does not execute generated shell/Slurm commands; it only returns scripts.

Safety / quality upgrades:
- Conservative clinical privacy redaction before external LLM calls.
- Environment-configurable, fault-tolerant Qdrant retrieval.
- Works across newer and older qdrant-client APIs where possible.
- Stable project filtering and duplicate-source suppression.
- Safer script generation and richer troubleshooting recipes.
"""
from __future__ import annotations

import logging
import os
import re
import shlex
from dataclasses import dataclass
from typing import Any, Iterable

try:  # Optional at import-time for tests/tools that do not install qdrant-client.
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qdrant_models
except Exception:  # pragma: no cover - dependency availability is environment-specific.
    QdrantClient = Any  # type: ignore[misc, assignment]
    qdrant_models = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)

_SAFE_TOKEN = re.compile(r"[^A-Za-z0-9_.:@/+,-=]")
_SAFE_SLURM_VALUE = re.compile(r"[^A-Za-z0-9_.:@/+,-=]")
_WORD_RE = re.compile(r"[A-Za-z0-9_+.-]+")

DEFAULT_DOC_COLLECTION = os.getenv("DOCUMENT_QDRANT_COLLECTION", "doc_chunks")
DEFAULT_QDRANT_VECTOR_NAME = os.getenv("DOCUMENT_QDRANT_VECTOR_NAME", "text").strip() or "text"
DEFAULT_RAG_LIMIT = int(os.getenv("RAG_RETRIEVAL_LIMIT", "5"))
MAX_RAG_LIMIT = int(os.getenv("RAG_RETRIEVAL_MAX_LIMIT", "20"))


def _clean_token(value: Any, default: str = "") -> str:
    """Return a compact label token safe for logs, Slurm fields, and paths."""
    text = str(value or default).strip()[:160]
    return _SAFE_TOKEN.sub("_", text) if text else default


def _clean_slurm_value(value: Any, default: str) -> str:
    text = str(value or default).strip()[:160]
    text = _SAFE_SLURM_VALUE.sub("_", text)
    return text or default


def _safe_int(value: Any, default: int, *, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(low, min(parsed, high))


def _safe_float(value: Any, default: float, *, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    return max(low, min(parsed, high))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _normalize_project_codes(project_codes: Iterable[Any] | None) -> set[str]:
    return {str(code).strip().upper() for code in (project_codes or []) if str(code).strip()}


def _payload_text(payload: dict[str, Any], max_chars: int = 1800) -> str:
    text = (
        payload.get("text_preview")
        or payload.get("excerpt")
        or payload.get("text")
        or payload.get("content")
        or payload.get("chunk_text")
        or ""
    )
    return str(text).strip()[:max_chars]


@dataclass(frozen=True)
class RetrievalConfig:
    collection_name: str = DEFAULT_DOC_COLLECTION
    vector_name: str | None = DEFAULT_QDRANT_VECTOR_NAME
    score_threshold: float | None = None
    max_preview_chars: int = 1800

    @classmethod
    def from_env(cls) -> "RetrievalConfig":
        raw_threshold = os.getenv("RAG_SCORE_THRESHOLD", "").strip()
        threshold = None
        if raw_threshold:
            threshold = _safe_float(raw_threshold, 0.0, low=0.0, high=1.0)
        return cls(
            collection_name=os.getenv("DOCUMENT_QDRANT_COLLECTION", DEFAULT_DOC_COLLECTION).strip() or DEFAULT_DOC_COLLECTION,
            vector_name=os.getenv("DOCUMENT_QDRANT_VECTOR_NAME", "text").strip() or "text",
            score_threshold=threshold,
            max_preview_chars=_safe_int(os.getenv("RAG_MAX_PREVIEW_CHARS", "1800"), 1800, low=200, high=6000),
        )


class PrivacyGuardrailAgent:
    """Redact patient identifiers before external LLM calls.

    This is intentionally conservative. It aims to preserve the research intent
    while removing obvious patient/person identifiers from the text that may be
    sent to a cloud model. It is not a replacement for a clinical DLP product,
    but it prevents the most common accidental leaks in this app.
    """

    _PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
        (re.compile(r"\b\d{6}[-+A][0-9A-Z]{3,4}\b", re.I), "Finnish national ID pattern", "[REDACTED_HETU]"),
        (re.compile(r"\bMRN[:\s#-]*[A-Z0-9-]{4,}\b", re.I), "Medical record number", "[REDACTED_MRN]"),
        (re.compile(r"\b(?:patient|pt|subject)\s*#?\s*[A-Z0-9-]{3,}\b", re.I), "Patient/subject identifier", "[REDACTED_PATIENT_ID]"),
        (re.compile(r"\b(?:sample|specimen|case)\s*#?\s*[A-Z]{1,6}[-_]?\d{4,}[A-Z0-9-]*\b", re.I), "Case/sample identifier", "[REDACTED_SAMPLE_ID]"),
        (re.compile(r"\b[A-Z]{2,}\d{6,}[A-Z0-9-]*\b"), "Alphanumeric identifier", "[REDACTED_IDENTIFIER]"),
        (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "Email address", "[REDACTED_EMAIL]"),
        (re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b"), "Phone-like number", "[REDACTED_PHONE]"),
        (re.compile(r"\b(?:DOB|date\s*of\s*birth)[:\s-]*\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", re.I), "Date of birth", "[REDACTED_DOB]"),
        (re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2}\b"), "Specific calendar date", "[REDACTED_DATE]"),
    ]

    @classmethod
    def audit_query(cls, question: str) -> dict[str, Any]:
        redacted = str(question or "")
        violations: list[str] = []
        redaction_count = 0

        for pattern, label, replacement in cls._PATTERNS:
            matches = list(pattern.finditer(redacted))
            if not matches:
                continue
            violations.append(label)
            redaction_count += len(matches)
            redacted = pattern.sub(replacement, redacted)

        unique_violations = list(dict.fromkeys(violations))
        risk_level = "low"
        if redaction_count >= 5:
            risk_level = "high"
        elif redaction_count > 0:
            risk_level = "blocked_for_external_llm"

        return {
            "is_safe": len(unique_violations) == 0,
            "violations": unique_violations,
            "redacted_text": redacted,
            "redaction_count": redaction_count,
            "risk_level": risk_level,
        }


class RAGAgent:
    """Retrieve documentation chunks from Qdrant with safe fallbacks."""

    def __init__(self, qdrant: QdrantClient, llm_client: Any, config: RetrievalConfig | None = None):
        self.qdrant = qdrant
        self.llm = llm_client
        self.config = config or RetrievalConfig.from_env()

    def retrieve(
        self,
        question: str,
        project_codes: list[str] | None = None,
        limit: int = DEFAULT_RAG_LIMIT,
    ) -> list[dict[str, Any]]:
        question = str(question or "").strip()
        if not question or self.qdrant is None:
            return []

        limit = max(1, min(int(limit or DEFAULT_RAG_LIMIT), MAX_RAG_LIMIT))
        try:
            vector = self.llm.embed(question)
        except Exception as exc:
            LOGGER.warning("Embedding generation failed before retrieval: %s", exc)
            return []

        hits = self._query_qdrant(vector=vector, limit=limit * 4)
        return self._normalize_hits(hits, project_codes=project_codes, limit=limit)

    def _query_qdrant(self, vector: list[float], limit: int) -> list[Any]:
        collection = self.config.collection_name
        using = self.config.vector_name
        threshold = self.config.score_threshold

        # Newer qdrant-client API.
        try:
            kwargs: dict[str, Any] = {
                "collection_name": collection,
                "query": vector,
                "limit": limit,
                "with_payload": True,
            }
            if using:
                kwargs["using"] = using
            if threshold is not None:
                kwargs["score_threshold"] = threshold
            response = self.qdrant.query_points(**kwargs)
            return list(getattr(response, "points", []) or [])
        except TypeError:
            # Some qdrant versions do not support `with_payload`, `using`, or `score_threshold` here.
            pass
        except Exception as exc:
            LOGGER.debug("qdrant.query_points primary attempt failed: %s", exc)

        try:
            kwargs = {
                "collection_name": collection,
                "query": vector,
                "limit": limit,
            }
            if using:
                kwargs["using"] = using
            response = self.qdrant.query_points(**kwargs)
            return list(getattr(response, "points", []) or [])
        except Exception as exc:
            LOGGER.debug("qdrant.query_points compatibility attempt failed: %s", exc)

        # Older qdrant-client API.
        try:
            kwargs = {
                "collection_name": collection,
                "query_vector": vector,
                "limit": limit,
                "with_payload": True,
            }
            if threshold is not None:
                kwargs["score_threshold"] = threshold
            return list(self.qdrant.search(**kwargs) or [])
        except Exception as exc:
            LOGGER.warning("Qdrant retrieval failed for collection %s: %s", collection, exc)
            return []

    def _normalize_hits(
        self,
        hits: list[Any],
        project_codes: list[str] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        allowed = _normalize_project_codes(project_codes)
        sources: list[dict[str, Any]] = []
        seen: set[str] = set()

        for hit in hits:
            payload = dict(getattr(hit, "payload", None) or {})
            if not payload:
                continue
            if not self._allowed_for_project(payload, allowed):
                continue

            chunk_id = str(payload.get("chunk_id") or payload.get("chunk_uid") or getattr(hit, "id", ""))
            source_uuid = str(
                payload.get("document_id")
                or payload.get("source_uuid")
                or payload.get("source_file_id")
                or payload.get("canonical_document_id")
                or payload.get("path")
                or payload.get("relative_path")
                or ""
            )
            dedupe_key = chunk_id or f"{source_uuid}:{payload.get('chunk_index')}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            text = _payload_text(payload, max_chars=self.config.max_preview_chars)
            if not text:
                continue

            score = getattr(hit, "score", None)
            try:
                score_f = float(score) if score is not None else 0.0
            except Exception:
                score_f = 0.0

            sources.append({
                "title": payload.get("title") or payload.get("document_title") or payload.get("filename") or "Document",
                "source_type": payload.get("source_type") or payload.get("document_kind") or payload.get("document_type") or "documentation",
                "source_uuid": source_uuid,
                "chunk_id": chunk_id or dedupe_key,
                "text_preview": text,
                "score": score_f,
                "project_code": payload.get("project_code"),
                "metadata": {
                    key: payload.get(key)
                    for key in ("filename", "relative_path", "section_id", "domain", "chunk_index", "ingestion_id")
                    if payload.get(key) is not None
                },
            })
            if len(sources) >= limit:
                break

        return sources

    @staticmethod
    def _allowed_for_project(payload: dict[str, Any], allowed: set[str]) -> bool:
        if not allowed:
            return True
        if payload.get("scope") == "lab":
            return True
        candidates = []
        candidates.extend(_as_list(payload.get("allowed_project_codes")))
        candidates.extend(_as_list(payload.get("project_codes")))
        candidates.extend(_as_list(payload.get("project_code")))
        normalized = _normalize_project_codes(candidates)
        # If a legacy payload has no project metadata, keep it visible rather than
        # silently hiding potentially useful lab documentation.
        return not normalized or not normalized.isdisjoint(allowed)


class InstallationSpecialist:
    """Return installation recipes for common spatial-biology tools."""

    _GUIDES: dict[str, dict[str, dict[str, Any]]] = {
        "napari": {
            "macos": {
                "status": "success",
                "commands": (
                    "curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh\n"
                    "bash Miniforge3-MacOSX-arm64.sh -b\n"
                    "source ~/miniforge3/bin/activate\n"
                    "mamba create -n napari_env python=3.10 napari pyqt -c conda-forge -y\n"
                    "conda activate napari_env\n"
                    "python - <<'PY'\nimport napari; print('napari', napari.__version__)\nPY"
                ),
                "verification": "napari --info",
                "expected_output": "Napari environment details are printed and a viewer window can be opened on a workstation.",
                "troubleshooting": "For Qt plugin failures, try `export QT_API=pyqt5`; on headless machines use a workstation, X11 forwarding, or offscreen checks only.",
            },
            "linux": {
                "status": "success",
                "commands": (
                    "mamba create -n napari_env python=3.10 napari pyqt -c conda-forge -y\n"
                    "conda activate napari_env\n"
                    "python - <<'PY'\nimport napari; print('napari', napari.__version__)\nPY"
                ),
                "verification": "napari --info",
                "expected_output": "Version and Qt backend information are printed.",
                "troubleshooting": "Install XCB libraries on Ubuntu/Debian nodes; avoid launching UI tools on compute nodes without a display.",
            },
        },
        "cylinter": {
            "linux": {
                "status": "success",
                "commands": (
                    "mamba create -n cylinter_env python=3.9 openjdk -c conda-forge -y\n"
                    "conda activate cylinter_env\n"
                    "python -m pip install --upgrade pip wheel setuptools\n"
                    "python -m pip install cylinter==0.1.5"
                ),
                "verification": "cylinter --help",
                "expected_output": "CLI help text is printed.",
                "troubleshooting": "Confirm `java -version` works inside the active environment before running image IO workflows.",
            },
        },
        "ashlar": {
            "linux": {
                "status": "success",
                "commands": (
                    "mamba create -n ashlar_env python=3.10 ashlar bioformats2raw raw2ometiff -c conda-forge -y\n"
                    "conda activate ashlar_env\n"
                    "ashlar --help"
                ),
                "verification": "ashlar --help",
                "expected_output": "Ashlar CLI help text is printed.",
                "troubleshooting": "For Bio-Formats reader errors, validate OME metadata, file naming, and channel naming before stitching.",
            },
        },
        "stardist": {
            "linux": {
                "status": "success",
                "commands": (
                    "mamba create -n stardist_env python=3.10 tensorflow stardist csbdeep tifffile -c conda-forge -y\n"
                    "conda activate stardist_env\n"
                    "python - <<'PY'\nfrom stardist.models import StarDist2D; print('StarDist OK')\nPY"
                ),
                "verification": "python -c \"from stardist.models import StarDist2D; print('ok')\"",
                "expected_output": "StarDist imports successfully.",
                "troubleshooting": "On Apple Silicon or CUDA hosts, align TensorFlow build with platform support before processing whole-slide images.",
            },
        },
        "qdrant": {
            "linux": {
                "status": "success",
                "commands": (
                    "docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v $PWD/qdrant_storage:/qdrant/storage qdrant/qdrant:latest\n"
                    "curl http://localhost:6333/collections"
                ),
                "verification": "curl http://localhost:6333/collections",
                "expected_output": "Qdrant returns a JSON collection list.",
                "troubleshooting": "If port 6333 is occupied, change the host port or stop the conflicting container.",
            }
        },
    }

    _ALIASES = {
        "basic": "ashlar",
        "basic-illumination": "ashlar",
        "stardist2d": "stardist",
        "vector-db": "qdrant",
        "vector_database": "qdrant",
    }

    def get_instructions(self, tool_name: str, os_platform: str) -> dict[str, Any]:
        tool = (tool_name or "").strip().lower().replace(" ", "_")
        tool = self._ALIASES.get(tool, tool)
        os_key = (os_platform or "linux").strip().lower()
        if os_key in {"ubuntu", "debian", "centos", "rocky"}:
            os_key = "linux"
        if os_key in {"darwin", "osx", "mac"}:
            os_key = "macos"

        guide = self._GUIDES.get(tool, {}).get(os_key)
        if not guide:
            available = {name: sorted(platforms.keys()) for name, platforms in self._GUIDES.items()}
            return {
                "status": "error",
                "message": f"No install guide for {tool_name!r} on {os_platform!r}.",
                "available_guides": available,
            }
        return {"status": "success", "tool": tool, "os": os_key, **guide}


class ScriptGeneratorAgent:
    """Generate production-safe shell wrappers."""

    def generate_bash(self, commands: str) -> str:
        body = str(commands or "").strip()
        if not body:
            body = "echo 'No commands were provided.'"
        return (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "IFS=$'\\n\\t'\n\n"
            "log() { printf '[%s] %s\\n' \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\" \"$*\"; }\n"
            "fail() { log \"ERROR: $*\"; exit 1; }\n\n"
            "log 'Starting generated OMEIA script'\n"
            "command -v python >/dev/null 2>&1 || log 'python not found on PATH; continuing if not required'\n\n"
            f"{body}\n"
            "log 'Finished successfully'\n"
        )


class LumiHpcAgent:
    """Generate LUMI-compatible Slurm scripts from API request specs."""

    def generate_job(self, spec: dict[str, Any]) -> str:
        spec = spec or {}
        use_gpu = bool(spec.get("use_gpu", True))
        job_name = _clean_slurm_value(spec.get("job_name"), "omeia_job")
        account = _clean_slurm_value(spec.get("project_account"), os.getenv("LUMI_PROJECT_ACCOUNT", "project_462001415"))
        partition = _clean_slurm_value(spec.get("partition") or ("small-g" if use_gpu else "small"), "small-g" if use_gpu else "small")
        nodes = _safe_int(spec.get("nodes"), 1, low=1, high=64)
        ntasks = _safe_int(spec.get("ntasks"), 1, low=1, high=4096)
        cpus = _safe_int(spec.get("cpus") or spec.get("cpus_per_task"), 8, low=1, high=256)
        gpus = _safe_int(spec.get("gpus_per_node") or (1 if use_gpu else 0), 1 if use_gpu else 0, low=0, high=8)
        mem = _clean_slurm_value(spec.get("memory"), "32G")
        walltime = _clean_slurm_value(spec.get("walltime") or spec.get("time"), "02:00:00")
        scratch = str(spec.get("scratch_path") or os.getenv("LUMI_SCRATCH", f"/scratch/{account}")).rstrip("/")
        log_dir = str(spec.get("log_dir") or "logs/pipeline").strip("/")
        work_dir = str(spec.get("work_dir") or scratch).rstrip("/")
        container = str(spec.get("container_sif") or spec.get("container") or "").strip()
        command = str(spec.get("execution_command") or spec.get("command") or "echo 'Set execution_command in request body'").strip()
        module_loads = [str(m).strip() for m in _as_list(spec.get("modules")) if str(m).strip()]
        env = dict(spec.get("env") or {})

        sbatch_lines = [
            "#!/usr/bin/env bash",
            f"#SBATCH --job-name={job_name}",
            f"#SBATCH --account={account}",
            f"#SBATCH --partition={partition}",
            f"#SBATCH --nodes={nodes}",
            f"#SBATCH --ntasks={ntasks}",
            f"#SBATCH --cpus-per-task={cpus}",
            f"#SBATCH --mem={mem}",
            f"#SBATCH --time={walltime}",
            f"#SBATCH --output={shlex.quote(log_dir)}/%x-%j.out",
            f"#SBATCH --error={shlex.quote(log_dir)}/%x-%j.err",
        ]
        if gpus:
            sbatch_lines.append(f"#SBATCH --gpus-per-node={gpus}")

        body = [
            "",
            "set -euo pipefail",
            "IFS=$'\\n\\t'",
            "module --force purge || true",
        ]
        for module in module_loads:
            body.append("module load " + shlex.quote(module))
        body.extend([
            "mkdir -p " + shlex.quote(f"{scratch}/{log_dir}"),
            "export APPTAINER_CACHEDIR=${APPTAINER_CACHEDIR:-" + shlex.quote(f"{scratch}/apptainer_cache") + "}",
            "mkdir -p \"$APPTAINER_CACHEDIR\"",
            "cd " + shlex.quote(work_dir),
            "echo \"[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Job started on $(hostname)\"",
            "echo \"SLURM_JOB_ID=${SLURM_JOB_ID:-manual}\"",
            "echo \"Working directory: $(pwd)\"",
        ])
        for key, value in env.items():
            clean_key = re.sub(r"[^A-Za-z0-9_]", "_", str(key).strip()).upper()
            if clean_key:
                body.append(f"export {clean_key}={shlex.quote(str(value))}")

        if container:
            body.extend([
                "test -f " + shlex.quote(container) + " || { echo 'Container not found: " + shlex.quote(container) + "'; exit 2; }",
                "apptainer exec " + ("--nv " if gpus else "")
                + "-B " + shlex.quote(scratch) + ":" + shlex.quote(scratch) + " "
                + shlex.quote(container) + " " + command,
            ])
        else:
            body.append(command)

        body.append("echo \"[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Job finished\"")
        return "\n".join(sbatch_lines + body) + "\n"


class TroubleshootingAgent:
    """Classify common spatial/HPC/LLM failures and return actionable fixes."""

    _RULES: list[tuple[tuple[str, ...], dict[str, str]]] = [
        (("opengl", "qt platform plugin"), {
            "cause": "Graphics/Qt initialization failure, common on headless SSH or minimal Linux nodes.",
            "fix": "Run UI tools on a workstation, enable X11 forwarding, or set `QT_QPA_PLATFORM=offscreen` for non-interactive checks.",
            "prevention": "Keep Napari/Qt workflows separate from compute-node batch jobs.",
        }),
        (("cuda", "out of memory"), {
            "cause": "GPU memory exhaustion during segmentation, training, or tiling.",
            "fix": "Reduce batch size/tile size, use mixed precision where safe, or request a larger GPU partition.",
            "prevention": "Profile peak VRAM on a representative slide before full-cohort submission.",
        }),
        (("oom",), {
            "cause": "Memory exhaustion; the scheduler or kernel likely killed the process.",
            "fix": "Increase `--mem`, reduce concurrency, or process slides/ROIs in smaller batches.",
            "prevention": "Log memory usage and keep one pilot run per modality.",
        }),
        (("killed", "memory"), {
            "cause": "The process was likely terminated by memory pressure.",
            "fix": "Lower worker count/tile size or request more memory.",
            "prevention": "Add memory telemetry to each batch and keep conservative defaults for full-slide runs.",
        }),
        (("no such file",), {
            "cause": "Missing input path, stale bind mount, or wrong working directory.",
            "fix": "Add preflight `test -e` checks for inputs, container, scratch folders, and output directories.",
            "prevention": "Use absolute scratch paths and generate scripts from a validated project manifest.",
        }),
        (("permission denied",), {
            "cause": "Filesystem permission or execute-bit issue.",
            "fix": "Check ownership, ACLs, and whether shell scripts are executable (`chmod +x`).",
            "prevention": "Write outputs into project scratch/work directories rather than read-only mounts.",
        }),
        (("401", "unauthorized"), {
            "cause": "Missing or expired authentication token.",
            "fix": "Refresh the session and verify frontend calls use the authenticated apiFetch wrapper.",
            "prevention": "Centralize API access and handle token refresh/session expiry consistently.",
        }),
        (("qdrant", "collection"), {
            "cause": "Vector collection is missing, misnamed, or has an incompatible vector dimension.",
            "fix": "Verify DOCUMENT_QDRANT_COLLECTION and embedding dimension, then recreate/reindex if needed.",
            "prevention": "Create collections through a migration/startup check and store model dimension metadata.",
        }),
        (("rate limit",), {
            "cause": "LLM provider rate limit or quota throttling.",
            "fix": "Retry with exponential backoff, reduce max tokens, or fall back to a local/mock provider.",
            "prevention": "Set provider budgets and keep local retrieval/mock mode available for demos.",
        }),
    ]

    def diagnose_log(self, log_text: str) -> dict[str, str]:
        lower = str(log_text or "").lower()
        for keywords, result in self._RULES:
            if all(k in lower for k in keywords):
                return {**result, "confidence": "high"}
        return {
            "cause": "Unclassified error; inspect the first traceback and the final stderr lines.",
            "fix": "Re-run the smallest failing command with verbose logging and preflight input checks.",
            "prevention": "Capture stdout/stderr, environment variables, package versions, and Slurm metadata for every run.",
            "confidence": "low",
        }


class ImagePipelineSpecialist:
    """Image-pipeline orchestration catalog."""

    _PIPELINES = [
        "basic", "ashlar", "stardist", "mesmer", "cycif", "geomx", "xenium", "qupath", "napari", "cylinter",
    ]

    def list_pipelines(self) -> list[str]:
        return list(self._PIPELINES)


class ClinicalSpatialSpecialist:
    """Return concise, reproducible analysis recipe templates."""

    def get_analysis_recipe(self, analysis_type: str) -> str:
        key = (analysis_type or "").strip().lower().replace("-", "_")
        recipes = {
            "survival": (
                "# Kaplan-Meier / Cox workflow\n"
                "from lifelines import KaplanMeierFitter, CoxPHFitter\n"
                "kmf = KaplanMeierFitter()\n"
                "kmf.fit(df['pfs_months'], event_observed=df['pfs_event'], label='cohort')\n"
                "ax = kmf.plot_survival_function(ci_show=True)\n"
                "cph = CoxPHFitter()\n"
                "cph.fit(df[['pfs_months', 'pfs_event', 'immune_infiltration_score']], 'pfs_months', 'pfs_event')\n"
                "cph.print_summary()\n"
            ),
            "group_compare": (
                "# Group comparison with auditable summary\n"
                "import pandas as pd\n"
                "from scipy import stats\n"
                "summary = df.groupby('hrd_status')['immune_infiltration_score'].agg(['count', 'mean', 'std'])\n"
                "groups = [g['immune_infiltration_score'].dropna().to_numpy() for _, g in df.groupby('hrd_status')]\n"
                "test = stats.ttest_ind(groups[0], groups[1], equal_var=False, nan_policy='omit')\n"
            ),
            "spatial_neighbors": (
                "# Squidpy neighborhood enrichment\n"
                "import squidpy as sq\n"
                "sq.gr.spatial_neighbors(adata, coord_type='generic')\n"
                "sq.gr.nhood_enrichment(adata, cluster_key='leiden')\n"
                "sq.pl.nhood_enrichment(adata, cluster_key='leiden')\n"
            ),
            "marker_qc": (
                "# Marker QC summary\n"
                "marker_cols = [c for c in df.columns if c.startswith('marker_')]\n"
                "qc = df[marker_cols].describe(percentiles=[.01, .05, .5, .95, .99]).T\n"
                "qc['dynamic_range'] = qc['99%'] - qc['1%']\n"
                "qc.sort_values('dynamic_range', ascending=False).head(20)\n"
            ),
        }
        aliases = {"cox": "survival", "km": "survival", "ttest": "group_compare", "neighbors": "spatial_neighbors"}
        key = aliases.get(key, key)
        return recipes.get(
            key,
            f"# No bundled recipe for {analysis_type!r}.\n"
            "# Available recipes: survival, group_compare, spatial_neighbors, marker_qc.\n",
        )
