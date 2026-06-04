"""OMEIA copilot specialist agents.

Premium drop-in upgrade:
- stronger local privacy guardrails before external LLM calls
- bounded, fault-tolerant Qdrant retrieval
- production-ready LUMI Slurm script generation
- richer installation/troubleshooting/clinical recipes
"""
from __future__ import annotations

import logging
import re
import shlex
from typing import Any

from qdrant_client import QdrantClient

LOGGER = logging.getLogger(__name__)

_SAFE_TOKEN = re.compile(r"[^A-Za-z0-9_.:@/+,\-=]")
_SAFE_SLURM_VALUE = re.compile(r"[^A-Za-z0-9_.:@/+,\-=]")


def _clean_token(value: Any, default: str = "") -> str:
    """Return a shell/Slurm-safe compact token for labels, accounts, partitions."""
    text = str(value or default).strip()[:160]
    return _SAFE_TOKEN.sub("_", text) if text else default


def _clean_slurm_value(value: Any, default: str) -> str:
    text = str(value or default).strip()[:160]
    text = _SAFE_SLURM_VALUE.sub("_", text)
    return text or default


class PrivacyGuardrailAgent:
    """Redact patient identifiers before external LLM calls.

    The guardrail is deliberately conservative for clinical-spatial research:
    it redacts identifiers while preserving the rest of the research question so
    local/mock models can continue answering from project-level context.
    """

    _PATTERNS: list[tuple[re.Pattern[str], str]] = [
        # Finnish HETU-ish: ddmmyy[+-A]xxxC. Kept broad to catch pasted IDs.
        (re.compile(r"\b\d{6}[-+A][0-9A-Z]{3,4}\b", re.I), "Finnish national ID pattern"),
        (re.compile(r"\bMRN[:\s#-]*[A-Z0-9-]{4,}\b", re.I), "Medical record number"),
        (re.compile(r"\b(?:patient|pt|subject)\s*#?\s*[A-Z0-9-]{3,}\b", re.I), "Patient/subject identifier"),
        (re.compile(r"\b[A-Z]{2,}\d{6,}[A-Z0-9-]*\b"), "Alphanumeric identifier"),
        (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "Email address"),
        (re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b"), "Phone-like number"),
        (re.compile(r"\b(?:DOB|date\s*of\s*birth)[:\s-]*\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", re.I), "Date of birth"),
    ]

    @classmethod
    def audit_query(cls, question: str) -> dict[str, Any]:
        redacted = question or ""
        violations: list[str] = []
        redaction_count = 0
        for pattern, label in cls._PATTERNS:
            matches = list(pattern.finditer(redacted))
            if matches:
                violations.append(label)
                redaction_count += len(matches)
                redacted = pattern.sub("[REDACTED]", redacted)

        return {
            "is_safe": len(violations) == 0,
            "violations": violations,
            "redacted_text": redacted,
            "redaction_count": redaction_count,
            "risk_level": "blocked_for_external_llm" if violations else "low",
        }


class RAGAgent:
    """Retrieve documentation chunks from Qdrant with safe fallbacks."""

    def __init__(self, qdrant: QdrantClient, llm_client: Any):
        self.qdrant = qdrant
        self.llm = llm_client

    def retrieve(
        self,
        question: str,
        project_codes: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        question = (question or "").strip()
        if not question:
            return []

        limit = max(1, min(int(limit or 5), 20))
        try:
            vector = self.llm.embed(question)
        except Exception as exc:
            LOGGER.warning("Embedding generation failed: %s", exc)
            return []

        try:
            response = self.qdrant.query_points(
                collection_name="doc_chunks",
                query=vector,
                using="text",
                limit=limit * 3,
            )
            hits = getattr(response, "points", []) or []
        except Exception as exc:
            LOGGER.warning("Qdrant doc_chunks retrieval failed: %s", exc)
            return []

        sources: list[dict[str, Any]] = []
        allowed = {str(code).upper() for code in (project_codes or []) if code}
        seen_chunks: set[str] = set()

        for hit in hits:
            payload = hit.payload or {}
            if allowed and payload.get("scope") != "lab":
                codes = payload.get("allowed_project_codes") or [payload.get("project_code")]
                normalized = {str(code).upper() for code in codes if code}
                if normalized and normalized.isdisjoint(allowed):
                    continue

            chunk_id = str(payload.get("chunk_id") or hit.id)
            if chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk_id)

            text = payload.get("text_preview") or payload.get("text") or payload.get("content") or ""
            sources.append({
                "title": payload.get("title") or payload.get("document_title") or "Document",
                "source_type": payload.get("source_type") or payload.get("document_kind") or "documentation",
                "source_uuid": payload.get("document_id") or payload.get("source_file_id") or payload.get("path") or "",
                "chunk_id": chunk_id,
                "text_preview": str(text)[:1600],
                "score": float(hit.score) if getattr(hit, "score", None) is not None else 0.0,
            })
            if len(sources) >= limit:
                break

        return sources


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
                "expected_output": "Napari environment details are printed and a window opens with `napari`.",
                "troubleshooting": "For Qt plugin failures, try `export QT_API=pyqt5`; on remote/headless machines use a workstation or X11 forwarding.",
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
                "troubleshooting": "For Bio-Formats reader errors, validate the input OME metadata and channel naming.",
            },
        },
    }

    def get_instructions(self, tool_name: str, os_platform: str) -> dict[str, Any]:
        tool = (tool_name or "").strip().lower()
        os_key = (os_platform or "linux").strip().lower()
        guide = self._GUIDES.get(tool, {}).get(os_key)
        if not guide:
            available = {
                name: sorted(platforms.keys())
                for name, platforms in self._GUIDES.items()
            }
            return {
                "status": "error",
                "message": f"No install guide for {tool_name!r} on {os_platform!r}.",
                "available_guides": available,
            }
        return {"status": "success", "tool": tool, "os": os_key, **guide}


class ScriptGeneratorAgent:
    """Generate production-safe shell wrappers."""

    def generate_bash(self, commands: str) -> str:
        body = (commands or "").strip()
        return (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "IFS=$'\\n\\t'\n\n"
            "log() { printf '[%s] %s\\n' \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\" \"$*\"; }\n\n"
            "log 'Starting generated OMEIA script'\n"
            f"{body}\n"
            "log 'Finished successfully'\n"
        )


class LumiHpcAgent:
    """Generate LUMI-compatible Slurm scripts from API request specs."""

    def generate_job(self, spec: dict[str, Any]) -> str:
        job_name = _clean_slurm_value(spec.get("job_name"), "omeia_job")
        account = _clean_slurm_value(spec.get("project_account"), "project_462001415")
        partition = _clean_slurm_value(spec.get("partition") or ("small-g" if spec.get("use_gpu", True) else "small"), "small-g")
        cpus = max(1, min(int(spec.get("cpus") or 8), 128))
        gpus = max(0, min(int(spec.get("gpus_per_node") or (1 if spec.get("use_gpu", True) else 0)), 8))
        mem = _clean_slurm_value(spec.get("memory"), "32G")
        walltime = _clean_slurm_value(spec.get("walltime") or spec.get("time"), "02:00:00")
        scratch = str(spec.get("scratch_path") or "/scratch/project_462001415").rstrip("/")
        log_dir = str(spec.get("log_dir") or "logs/pipeline").strip("/")
        container = str(spec.get("container_sif") or "").strip()
        command = str(spec.get("execution_command") or spec.get("command") or "echo 'Set execution_command in request body'").strip()

        sbatch_lines = [
            "#!/usr/bin/env bash",
            f"#SBATCH --job-name={job_name}",
            f"#SBATCH --account={account}",
            f"#SBATCH --partition={partition}",
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
            "mkdir -p " + shlex.quote(f"{scratch}/{log_dir}"),
            "export APPTAINER_CACHEDIR=${APPTAINER_CACHEDIR:-" + shlex.quote(f"{scratch}/apptainer_cache") + "}",
            "mkdir -p \"$APPTAINER_CACHEDIR\"",
            "echo \"[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Job started on $(hostname)\"",
            "echo \"SLURM_JOB_ID=${SLURM_JOB_ID:-manual}\"",
        ]

        if container:
            body.extend([
                "test -f " + shlex.quote(container) + " || { echo 'Container not found'; exit 2; }",
                "apptainer exec " + ("--nv " if gpus else "") +
                "-B " + shlex.quote(scratch) + ":" + shlex.quote(scratch) + " " +
                shlex.quote(container) + " " + command,
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
        (("no such file", "filenotfounderror"), {
            "cause": "Missing input path, stale bind mount, or wrong working directory.",
            "fix": "Add preflight `test -e` checks for inputs, container, scratch folders, and output directories.",
            "prevention": "Use absolute scratch paths and generate scripts from a validated project manifest.",
        }),
        (("permission denied",), {
            "cause": "Filesystem permission or execute-bit issue.",
            "fix": "Check ownership, ACLs, and whether shell scripts are executable (`chmod +x`).",
            "prevention": "Write outputs into project scratch/work directories rather than read-only mounts.",
        }),
    ]

    def diagnose_log(self, log_text: str) -> dict[str, str]:
        lower = (log_text or "").lower()
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

    def list_pipelines(self) -> list[str]:
        return ["cycif", "geomx", "xenium", "mesmer", "qupath", "ashlar", "basic", "stardist"]


class ClinicalSpatialSpecialist:
    """Return concise, reproducible analysis recipe templates."""

    def get_analysis_recipe(self, analysis_type: str) -> str:
        key = (analysis_type or "").strip().lower()
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
                "a, b = [g['immune_infiltration_score'].to_numpy() for _, g in df.groupby('hrd_status')][:2]\n"
                "test = stats.ttest_ind(a, b, equal_var=False, nan_policy='omit')\n"
            ),
            "spatial_neighbors": (
                "import squidpy as sq\n"
                "sq.gr.spatial_neighbors(adata, coord_type='generic')\n"
                "sq.gr.nhood_enrichment(adata, cluster_key='leiden')\n"
                "sq.pl.nhood_enrichment(adata, cluster_key='leiden')\n"
            ),
        }
        return recipes.get(
            key,
            f"# No bundled recipe for {analysis_type!r}.\n"
            "# Use /clinical/survival or /clinical/group-compare APIs for registered synthetic runs.\n",
        )
