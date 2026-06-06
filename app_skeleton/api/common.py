from __future__ import annotations

import json

import os

import re

import math

import hashlib

import logging

import subprocess

from contextlib import asynccontextmanager

from datetime import datetime

from pathlib import Path

from typing import List, Dict, Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Query

from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field

from dotenv import load_dotenv

import psycopg

from qdrant_client import QdrantClient

from qdrant_client.http import models

from app_skeleton.api.llm_client import LLMClient

from app_skeleton.api.project_processor import (
    get_digital_twin, process_project, PROCESSED_DIR, update_digital_twin, get_content_root,
    save_processed, sync_public_processed, get_project_file_preview_text,
    PROJECT_EXTRACTABLE_EXTENSIONS,
)

from app_skeleton.api.paths import (
    PROJECTS_ROOT,
    DATABASE_ROOT,
    CSC_MEDIA_DIR,
    checker_script,
    CATALOG_PATH,
    PUBLIC_PROCESSED_DIR,
    safe_relative_path,
)

from app_skeleton.api.database_sections import (
    DATABASE_SECTIONS,
    section_root,
    list_sections,
    assert_all_section_roots_exist,
)

from app_skeleton.api.raw_vault_store import (
    load_summary as vault_summary,
    search_vault,
    review_queue as vault_review_queue,
    rebuild_inventory as vault_rebuild_inventory,
    sync_inventory_to_postgres,
    deduplication_report,
    vault_manifest_page,
    mark_asset_reviewed,
)

from app_skeleton.api.vault_ingestion_engine import (
    run_ingest_scan,
    ingest_project as vault_ingest_project,
    retry_failed_extractions,
)

from app_skeleton.api.page_registry import list_domains, list_sections as list_page_sections

from app_skeleton.api.document_registry import list_documents as list_registry_documents

from app_skeleton.api import platform_admin

from app_skeleton.api.auth_firebase import require_admin, require_firebase_user

from app_skeleton.api import datapad_service as datapad

from app_skeleton.api.datapad_service import ConflictError

_FIREBASE_PROTECTED = [Depends(require_firebase_user)]

from app_skeleton.api.supabase_sync import (
    sync_documents_to_supabase,
    supabase_sync_status,
    read_last_sync_report,
)

from app_skeleton.storage import datacloud_webdav, pdrive_smb

from app_skeleton.storage import ingestion as storage_ingestion

from fastapi.responses import StreamingResponse

from app_skeleton.api.database_processor import (
    get_section_record,
    process_all_sections,
    list_processed_summary,
    list_lab_sections_detail,
    section_summary_for_api,
    section_detail_for_api,
    section_documents_for_api,
    search_section_chunks,
    save_processed_section,
    load_processed_section,
    write_lab_manifest,
    _iter_chunks_from_disk,
)

from app_skeleton.api.lab_knowledge_store import (
    ingest_all_lab_sections,
    ingest_section_to_database,
    search_lab_knowledge,
    get_lab_index_stats,
    LAB_CORPUS,
)

from app_skeleton.api.document_extraction import _extract_file

from app_skeleton.api.feature_warehouse import (
    seed_feature_warehouse,
    list_feature_definitions,
    list_feature_matrices,
    get_sample_features,
    find_similar_samples,
)

from app_skeleton.api.clinical_tools import (
    run_survival_analysis,
    run_group_comparison,
    register_analysis_run,
    list_analysis_runs,
    get_clinical_variables,
)

from app_skeleton.api.agents import (
    PrivacyGuardrailAgent,
    RAGAgent,
    InstallationSpecialist,
    LumiHpcAgent,
    ImagePipelineSpecialist,
    TroubleshootingAgent,
    ScriptGeneratorAgent,
    ClinicalSpatialSpecialist
)

_BLUEPRINT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(_BLUEPRINT_ROOT / "configs" / ".env")

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

LOGGER = logging.getLogger(__name__)

@asynccontextmanager
async def _app_lifespan(application: FastAPI):
    from app_skeleton.api.firebase_app import init_firebase_if_configured

    init_firebase_if_configured()
    yield

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

from app_skeleton.api.supabase_config import postgres_conn

DB_CONN = postgres_conn()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

qdrant_client = QdrantClient(url=QDRANT_URL)

llm_client = LLMClient()

rag_agent = RAGAgent(qdrant_client, llm_client)

install_agent = InstallationSpecialist()

hpc_agent = LumiHpcAgent()

pipeline_agent = ImagePipelineSpecialist()

troubleshooting_agent = TroubleshootingAgent()

script_agent = ScriptGeneratorAgent()

clinical_agent = ClinicalSpatialSpecialist()

_CATALOG_PATH = Path(CATALOG_PATH)

_projects_catalog_cache: Optional[List[Dict[str, Any]]] = None

def load_projects_catalog() -> List[Dict[str, Any]]:
    """Load project catalog once, with JSON-error tolerance."""
    global _projects_catalog_cache
    if _projects_catalog_cache is not None:
        return _projects_catalog_cache
    try:
        if _CATALOG_PATH.exists():
            data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
            _projects_catalog_cache = data if isinstance(data, list) else []
        else:
            _projects_catalog_cache = []
    except Exception as exc:
        LOGGER.warning("Failed to load projects catalog %s: %s", _CATALOG_PATH, exc)
        _projects_catalog_cache = []
    return _projects_catalog_cache

def merge_with_catalog(db_project: Dict[str, Any]) -> Dict[str, Any]:
    catalog_by_code = {p["project_code"]: p for p in load_projects_catalog()}
    cat = catalog_by_code.get(db_project.get("project_code", ""), {})
    merged = {**cat, **{k: v for k, v in db_project.items() if v not in (None, "", [], "TBD", "None", "Not defined.")}}
    for key in ("project_summary", "research_question", "collaborators", "modalities", "members"):
        if not merged.get(key) and cat.get(key):
            merged[key] = cat[key]
    return merged

def project_catalog_coverage() -> dict[str, Any]:
    """Mark catalog projects with zero processed assets as needs confirmation."""
    catalog = load_projects_catalog()
    needs: list[dict[str, Any]] = []
    covered: list[dict[str, Any]] = []
    for entry in catalog:
        code = (entry.get("project_code") or "").strip()
        if not code:
            continue
        twin_path = PROCESSED_DIR / f"{code}.json"
        asset_count = 0
        mapping_status = "missing_source_mapping"
        if twin_path.is_file():
            try:
                twin = json.loads(twin_path.read_text(encoding="utf-8"))
                asset_count = int(
                    twin.get("total_assets_count")
                    or (twin.get("content_library") or {}).get("totals", {}).get("all")
                    or 0
                )
            except Exception:
                asset_count = 0
            mapping_status = "processed" if asset_count > 0 else "empty_twin"
        row = {
            "project_code": code,
            "project_name": entry.get("project_name") or code,
            "mapping_status": mapping_status,
            "asset_count": asset_count,
        }
        if mapping_status != "processed":
            needs.append(row)
        else:
            covered.append(row)
    return {
        "catalog_count": len(catalog),
        "processed_count": len(covered),
        "needs_confirmation_count": len(needs),
        "needs_confirmation": needs,
    }

def fetch_projects_unified() -> List[Dict[str, Any]]:
    catalog = load_projects_catalog()
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT p.project_id, p.project_code, p.project_name, p.disease_focus,
                           p.principal_investigator, p.project_lead, p.start_date, p.end_date, p.status,
                           pe.project_short_title, pe.research_question, pe.project_type, pe.priority,
                           pe.collaborators, pe.ethics_approval_reference, pe.current_blockers,
                           pe.next_actions, pe.project_summary, pe.latest_update
                    FROM core.project p
                    LEFT JOIN platform.project_extension pe ON p.project_id = pe.project_id
                    ORDER BY p.project_code;
                """)
                rows = cur.fetchall()
                if rows:
                    result = []
                    for r in rows:
                        pid = r[0]
                        cur.execute("""
                            SELECT r.full_name, pm.role
                            FROM platform.project_member pm
                            JOIN platform.researcher r ON pm.researcher_id = r.researcher_id
                            WHERE pm.project_id = %s;
                        """, (pid,))
                        members = [{"name": row[0], "role": row[1]} for row in cur.fetchall()]
                        db_proj = {
                            "project_id": str(pid),
                            "project_code": r[1],
                            "project_name": r[2],
                            "disease_focus": r[3],
                            "principal_investigator": r[4],
                            "project_lead": r[5],
                            "start_date": str(r[6]) if r[6] else None,
                            "end_date": str(r[7]) if r[7] else None,
                            "status": r[8],
                            "project_short_title": r[9] or r[1],
                            "research_question": r[10] or "",
                            "project_type": r[11] or "spatial_profiling",
                            "priority": r[12] or "medium",
                            "collaborators": r[13] or [],
                            "ethics_approval_reference": r[14] or "",
                            "current_blockers": r[15] or "",
                            "next_actions": r[16] or "",
                            "project_summary": r[17] or "",
                            "latest_update": r[18] or "",
                            "members": members,
                        }
                        result.append(merge_with_catalog(db_proj))
                    seen = {p["project_code"] for p in result}
                    for cat_proj in catalog:
                        if cat_proj["project_code"] not in seen:
                            result.append({**cat_proj, "project_id": f"cat-{cat_proj['project_index']}"})
                    result.sort(key=lambda p: (p.get("project_index", 999), p.get("project_code", "")))
                    return result
    except Exception as exc:
        LOGGER.warning("Project DB lookup failed, using catalog fallback: %s", exc)
    return [{**p, "project_id": f"cat-{p.get('project_index', idx)}"} for idx, p in enumerate(catalog, start=1)]

class QuestionRequest(BaseModel):
    question: str
    project_codes: List[str] = Field(default_factory=list)
    mode: str = "documentation_only"
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None

class SourceInfo(BaseModel):
    title: str
    source_type: str
    source_uuid: str
    chunk_id: Optional[str] = None
    text_preview: str
    score: float
    nav: Optional[Dict[str, Any]] = None
    bucket: Optional[str] = None

class QuestionResponse(BaseModel):
    answer: str
    limitations: List[str]
    sources: List[SourceInfo]
    database_counts: Dict[str, Any] = Field(default_factory=dict)
    is_safe: bool = True
    search_hits: List[Dict[str, Any]] = Field(default_factory=list)
    provider: str = "mock"
    effective_provider: str = "mock"
    model: str = "mock-model"
    fallback_used: bool = False
    synthesis_mode: str = "mock"
    intent: str = "general_chat"
    use_rag: bool = False
    show_sources: bool = False
    require_citations: bool = False
    answer_style: str = "natural"
    reason: str = ""
    blocked_by_guardrail: bool = False

class InstallRequest(BaseModel):
    tool_name: str
    os_platform: str

class LumiJobRequest(BaseModel):
    job_name: str = "lumi_mesmer_run"
    project_account: str = "project_462001415"
    use_gpu: bool = True
    cpus: int = 8
    memory: str = "32G"
    walltime: str = "02:00:00"
    scratch_path: str = "/scratch/project_462001415"
    log_dir: str = "logs/pipeline"
    input_path: str = "/scratch/project_462001415/image_processing/ada/stitched"
    container_sif: str = "/scratch/project_462001415/containers/deepcell-mesmer_latest.sif"
    execution_command: str = "python /scratch/project_462001415/scripts/segment.py --compartment cell"

class LogParseRequest(BaseModel):
    log_text: str

class CheckerRequest(BaseModel):
    checker_name: str  # 'python_env', 'gpu', 'napari', 'docker', 'lumi_modules', 'cylinter_inputs', 'project_structure'

class SurvivalRequest(BaseModel):
    duration_col: str = "pfs_months"
    event_col: str = "pfs_event"
    group_col: str = "brca_status"
    project_code: Optional[str] = None
    register_run: bool = True

class GroupCompareRequest(BaseModel):
    feature_col: str = "immune_infiltration_score"
    group_col: str = "hrd_status"
    project_code: Optional[str] = None
    register_run: bool = True

class SimilarityRequest(BaseModel):
    sample_code: str
    project_code: Optional[str] = None
    limit: int = 5

def _clinical_context_for_question(question: str, project_codes: List[str]) -> str:
    """Inject Phase 3/4 structured results when query matches clinical/feature intents."""
    q = question.lower()
    proj = project_codes[0] if project_codes else None
    blocks = []

    if any(k in q for k in ("survival", "kaplan", "pfs", "progression-free", "overall survival", "os curve")):
        res = run_survival_analysis(project_code=proj)
        blocks.append(f"Survival analysis (synthetic):\n{json.dumps(res, indent=2)}")

    if any(k in q for k in ("compare", "group", "difference", "hrd", "brca")) and any(k in q for k in ("feature", "density", "infiltration", "score")):
        feat = "immune_infiltration_score"
        for name in ("tumor_cell_density", "cd8_tcell_density", "hrd_signature_score", "immune_infiltration_score"):
            if name.replace("_", " ") in q or name in q:
                feat = name
                break
        res = run_group_comparison(feature_col=feat, project_code=proj)
        blocks.append(f"Group comparison (synthetic):\n{json.dumps(res, indent=2)}")

    if any(k in q for k in ("similar sample", "similarity", "nearest neighbor", "match sample")):
        sample = "SYNTH_SAMPLE_001"
        for token in question.upper().split():
            if token.startswith("SYNTH_SAMPLE_"):
                sample = token
                break
        sims = find_similar_samples(sample, limit=5, project_code=proj)
        blocks.append(f"Feature similarity for {sample}:\n{json.dumps(sims, indent=2)}")

    if any(k in q for k in ("feature matrix", "feature warehouse", "spatial feature", "feature definition")):
        defs = list_feature_definitions()[:12]
        blocks.append(f"Feature registry ({len(defs)} shown):\n{json.dumps(defs, indent=2)}")

    return "\n\n".join(blocks)

class ProjectExtensionUpdate(BaseModel):
    project_short_title: Optional[str] = None
    research_question: Optional[str] = None
    project_type: Optional[str] = None
    priority: Optional[str] = None
    collaborators: Optional[List[str]] = None
    ethics_approval_reference: Optional[str] = None
    current_blockers: Optional[str] = None
    next_actions: Optional[str] = None
    project_summary: Optional[str] = None
    latest_update: Optional[str] = None

class NotebookEntryCreate(BaseModel):
    project_code: str
    sample_code: Optional[str] = None
    title: str
    content: str
    conclusions: Optional[str] = None
    issues_found: Optional[str] = None
    next_steps: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    entry_type: str = "general_note"
    visibility_level: str = "internal"

class NotebookEntryUpdate(BaseModel):
    title: str
    content: str
    conclusions: Optional[str] = None
    issues_found: Optional[str] = None
    next_steps: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    entry_type: str = "general_note"

class DecisionCreate(BaseModel):
    project_code: str
    title: str
    decision_details: str
    rationale: str
    alternatives_considered: Optional[str] = None
    decided_by_username: str = "debdeba"
    decision_date: Optional[str] = None
    linked_notebook_entry_id: Optional[str] = None
    linked_dataset_id: Optional[str] = None

class WikiPageCreate(BaseModel):
    title: str
    slug: str
    content: str
    wiki_type: str = "SOP"
    project_code: Optional[str] = None

class WikiPageUpdate(BaseModel):
    title: str
    content: str
    wiki_type: str = "SOP"

class TaskCreate(BaseModel):
    project_code: str
    sample_code: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[str] = None

class TaskUpdate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[str] = None

def query_postgres_metadata(project_codes: Optional[List[str]] = None) -> Dict[str, Any]:
    """Queries PostgreSQL for core summary counts to prevent hallucinations, with optional project scope filtering."""
    data = {}
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                if project_codes:
                    # Filtered patient counts
                    cur.execute("""
                        SELECT COUNT(DISTINCT s.patient_id) 
                        FROM core.sample s
                        JOIN core.project p ON s.project_id = p.project_id
                        WHERE p.project_code = ANY(%s);
                    """, (project_codes,))
                    data["patient_count"] = cur.fetchone()[0]
                    
                    # Filtered sample counts
                    cur.execute("""
                        SELECT COUNT(s.sample_id) 
                        FROM core.sample s
                        JOIN core.project p ON s.project_id = p.project_id
                        WHERE p.project_code = ANY(%s);
                    """, (project_codes,))
                    data["sample_count"] = cur.fetchone()[0]
                    
                    # Filtered project breakdowns
                    cur.execute("""
                        SELECT p.project_code, COUNT(s.sample_id) 
                        FROM core.project p
                        LEFT JOIN core.sample s ON p.project_id = s.project_id
                        WHERE p.project_code = ANY(%s)
                        GROUP BY p.project_code;
                    """, (project_codes,))
                    data["project_samples"] = {row[0]: row[1] for row in cur.fetchall()}

                    # Filtered modality breakdowns
                    cur.execute("""
                        SELECT s.metadata->>'modality' as mod, COUNT(s.sample_id) 
                        FROM core.sample s
                        JOIN core.project p ON s.project_id = p.project_id
                        WHERE p.project_code = ANY(%s)
                        GROUP BY mod;
                    """, (project_codes,))
                    data["modality_samples"] = {row[0] or "unknown": row[1] for row in cur.fetchall()}
                else:
                    # Patient counts
                    cur.execute("SELECT COUNT(*) FROM core.patient;")
                    data["patient_count"] = cur.fetchone()[0]
                    
                    # Sample counts
                    cur.execute("SELECT COUNT(*) FROM core.sample;")
                    data["sample_count"] = cur.fetchone()[0]
                    
                    # Project breakdowns
                    cur.execute("""
                        SELECT p.project_code, COUNT(s.sample_id) 
                        FROM core.project p
                        LEFT JOIN core.sample s ON p.project_id = s.project_id
                        GROUP BY p.project_code;
                    """)
                    data["project_samples"] = {row[0]: row[1] for row in cur.fetchall()}

                    # Modality breakdowns
                    cur.execute("""
                        SELECT metadata->>'modality' as mod, COUNT(*) 
                        FROM core.sample 
                        GROUP BY mod;
                    """)
                    data["modality_samples"] = {row[0] or "unknown": row[1] for row in cur.fetchall()}
    except Exception as exc:
        LOGGER.warning("Postgres metadata query failed: %s", exc)
        data["error"] = str(exc)
        data["patient_count"] = 0
        data["sample_count"] = 0
        data["project_samples"] = {}
        data["modality_samples"] = {}
    return data

def auto_log_notebook_entry(conn, project_id, author_id, title, content, entry_type="general_note", sample_id=None, pipeline_stage=None):
    with conn.cursor() as cur:
        # Insert notebook entry
        cur.execute("""
            INSERT INTO platform.notebook_entry (project_id, sample_id, title, pipeline_stage, author_id, content, entry_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING entry_id;
        """, (project_id, sample_id, title, pipeline_stage, author_id, content, entry_type))
        entry_id = cur.fetchone()[0]

        # Insert revision 1
        cur.execute("""
            INSERT INTO platform.notebook_revision (entry_id, revision_number, title, content, author_id)
            VALUES (%s, 1, %s, %s, %s);
        """, (entry_id, title, content, author_id))

        # Insert auto log audit
        cur.execute("""
            INSERT INTO platform.auto_log (project_id, event_type, description, linked_object_type, linked_object_id)
            VALUES (%s, %s, %s, 'notebook_entry', %s);
        """, (project_id, f"auto_{entry_type}", f"Action Logged: {title}", entry_id))
        return entry_id

class ProjectCreate(BaseModel):
    project_code: str
    project_name: str
    project_lead: str
    principal_investigator: str = "Anniina Färkkilä, MD, PhD"
    short_description: str
    disease_focus: str = "Ovarian Cancer"
    default_sensitivity: str = "restricted"
    status: str = "active"
    
    # Extension fields
    project_type: str = "translational_research"
    priority: str = "medium"
    ethics_approval_reference: str = "TBD"
    current_blockers: str = "None"
    next_actions: str = "TBD"
    project_summary: str = ""
    collaborators: List[str] = Field(default_factory=list)

class DocumentIngestRequest(BaseModel):
    filename: str
    file_type: str
    extracted_text: str
    tags: List[str] = Field(default_factory=list)
    project_code: Optional[str] = None
    software_associations: List[str] = Field(default_factory=list)
    pipeline_stage_associations: List[str] = Field(default_factory=list)
    metadata_dict: Dict[str, Any] = Field(default_factory=dict)

class ChecklistToggleRequest(BaseModel):
    checklist_id: str
    status: str
    username: str = "debdeba"

import pathlib

import mimetypes

from fastapi.responses import FileResponse

SAFE_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".pyw", ".pyi", ".r", ".rmd", ".sh", ".bash", ".zsh", ".fish",
    ".ps1", ".psm1", ".bat", ".cmd", ".json", ".jsonl", ".yaml", ".yml", ".sql", ".csv", ".tsv",
    ".toml", ".ini", ".cfg", ".log", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".go",
    ".rs", ".rb", ".php", ".pl", ".lua", ".swift", ".kt", ".scala", ".vb", ".cs", ".cpp", ".c",
    ".h", ".hpp", ".ipynb", ".html", ".htm", ".xml", ".vue", ".svelte", ".tf", ".hcl", ".proto",
    ".graphql", ".gql", ".jl", ".nim", ".zig", ".awk", ".sed", ".tcl", ".ex", ".exs", ".erl",
    ".hs", ".fs", ".clj", ".dart", ".groovy", ".m", ".mm", ".f", ".f90", ".v", ".sv", ".vhd",
}

MAX_PROJECT_FILE_READ_BYTES = int(os.getenv("MAX_PROJECT_FILE_READ_BYTES", str(2 * 1024 * 1024)))

MAX_PROJECT_FILE_WRITE_BYTES = int(os.getenv("MAX_PROJECT_FILE_WRITE_BYTES", str(2 * 1024 * 1024)))

def _resolve_under(root: str | Path, relative_path: str) -> Path:
    root_path = Path(root).resolve()
    candidate = (root_path / relative_path).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Access denied.") from exc
    return candidate

def _is_safe_text_file(path: Path) -> bool:
    return path.suffix.lower() in SAFE_TEXT_EXTENSIONS

def _is_database_asset_file(path: Path) -> bool:
    ext = path.suffix.lower()
    if _is_safe_text_file(path):
        return True
    return ext in {
        ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".tif", ".tiff",
        ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt",
    }

DATABASE_EXTRACTABLE_EXTENSIONS = {
    ".pdf", ".docx", ".dotx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".odt", ".csv", ".tsv", ".rtf",
}

def _is_database_extractable(path: Path) -> bool:
    return path.suffix.lower() in DATABASE_EXTRACTABLE_EXTENSIONS

SKIP_DATABASE_DIR_NAMES = {".git", "node_modules", ".venv", ".dart_tool", "build", "dist", ".next", "__pycache__", ".DS_Store"}

class LabIngestRequest(BaseModel):
    refresh_extract: bool = False

from app_skeleton.api.project_knowledge_extractor import extract_and_ingest_project

_LAB_FILE_BROWSER_DEPRECATED = (
    "Lab corpus uses canonical search (/api/knowledge/lab/search) and processed twins; "
    "raw file tree browsing is disabled."
)

def _database_static_url(section_id: str, relative_path: str) -> str:
    from urllib.parse import quote

    meta = DATABASE_SECTIONS[section_id]
    rel_root = meta["relative_root"].strip("/")
    rel_file = relative_path.strip().lstrip("/").replace("\\", "/")
    combined = "/".join(p for p in (rel_root, rel_file) if p)
    return "/database-static/" + "/".join(quote(seg, safe="") for seg in combined.split("/"))

def get_project_folder_path(project_code: str) -> Optional[str]:
    root = get_content_root(project_code)
    return str(root) if root else None

def scan_project_text_files(folder_path: str) -> list:
    text_files = []
    root_path = Path(folder_path).resolve() if folder_path else None
    if not root_path or not root_path.exists():
        return text_files
    skip_parts = {".git", "node_modules", ".venv", ".dart_tool", "build", "dist", ".next", "__pycache__"}
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in skip_parts]
        for file in files:
            file_path = Path(root) / file
            if any(part in skip_parts for part in file_path.parts):
                continue
            if not _is_safe_text_file(file_path):
                continue
            try:
                if file_path.stat().st_size > MAX_PROJECT_FILE_READ_BYTES:
                    continue
                rel_path = str(file_path.resolve().relative_to(root_path))
            except Exception:
                continue
            text_files.append({"name": rel_path, "path": str(file_path)})
    return sorted(text_files, key=lambda item: item["name"])

def parse_log_timeline(content: str) -> list:
    lines = content.split("\n")
    entries = []
    current_entry = None
    
    date_pattern = re.compile(r"^(?:#+\s*)?(\d{1,2}\.\d{1,2}\.\d{4})")
    
    for line in lines:
        match = date_pattern.match(line.strip())
        if match:
            if current_entry:
                entries.append(current_entry)
            date_str = match.group(1)
            title = line.replace(match.group(0), "").strip(" -*#\t")
            if not title:
                title = f"Log Entry for {date_str}"
            current_entry = {
                "date": date_str,
                "title": title,
                "content": ""
            }
        else:
            if current_entry:
                current_entry["content"] += line + "\n"
            else:
                if line.strip():
                    current_entry = {
                        "date": "Overview",
                        "title": "General Project Notes",
                        "content": line + "\n"
                    }
                    
    if current_entry:
        entries.append(current_entry)
        
    for entry in entries:
        entry["content"] = entry["content"].strip()
        if entry["title"].startswith("Log Entry for") and entry["content"]:
            first_line = entry["content"].split("\n")[0].strip(" -*#\t")
            if first_line and len(first_line) < 60 and (first_line.startswith("*") or first_line.startswith("#") or first_line.startswith("Meeting") or first_line.startswith("To do")):
                entry["title"] = first_line.replace("*", "").replace("#", "").strip()
                
    return entries

class FileWriteRequest(BaseModel):
    project_code: str
    relative_path: str
    content: str

PROJECT_ASSET_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".py": "text/plain; charset=utf-8",
    ".pyw": "text/plain; charset=utf-8",
    ".r": "text/plain; charset=utf-8",
    ".sh": "text/plain; charset=utf-8",
    ".bash": "text/plain; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".jsx": "text/javascript; charset=utf-8",
    ".ts": "text/typescript; charset=utf-8",
    ".tsx": "text/typescript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".yaml": "text/yaml; charset=utf-8",
    ".yml": "text/yaml; charset=utf-8",
    ".sql": "text/plain; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".ipynb": "application/json; charset=utf-8",
}

def _project_asset_disposition(filename: str, ext: str) -> str:
    from urllib.parse import quote
    safe = filename.replace('"', "'")
    encoded = quote(filename)
    inline_ext = {
        ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".tif", ".tiff",
        *SAFE_TEXT_EXTENSIONS,
    }
    disp = "inline" if ext in inline_ext else "attachment"
    return f'{disp}; filename="{safe}"; filename*=UTF-8\'\'{encoded}'

class DatapadSaveRequest(BaseModel):
    project_code: str
    relative_path: str
    content: str
    create_backup: bool = True
    expected_etag: str | None = None

class DatapadContentRequest(BaseModel):
    content: str
    doc_type: str = "markdown"

class DatapadApplyPatchesRequest(BaseModel):
    project_code: str
    relative_path: str
    patches: list[dict[str, Any]] = Field(default_factory=list)
    expected_etag: str | None = None

class DatapadRestoreRequest(BaseModel):
    project_code: str
    relative_path: str
    backup_path: str

def _datapad_actor(user: dict[str, Any]) -> str:
    return (user.get("email") or user.get("uid") or "unknown").strip()

__all__ = [name for name in globals() if not name.startswith('__')]
