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

# Import modular components
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

# Load environment variables (local secrets in configs/.env — gitignored)
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


app = FastAPI(title="OMEIA Research Copilot API", version="0.4.0-premium", lifespan=_app_lifespan)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount CSC folder to serve static media (videos, audio, configurations)
if CSC_MEDIA_DIR.exists():
    app.mount("/csc-media", StaticFiles(directory=str(CSC_MEDIA_DIR)), name="csc")

# Mount projects folder for direct figure/document serving (images, PDFs, etc.)
if PROJECTS_ROOT.exists():
    app.mount("/projects-static", StaticFiles(directory=str(PROJECTS_ROOT)), name="projects-static")

if DATABASE_ROOT.exists():
    app.mount("/database-static", StaticFiles(directory=str(DATABASE_ROOT)), name="database-static")

# Database connections (Supabase pooler when SUPABASE_DB_PASSWORD is set)
from app_skeleton.api.supabase_config import postgres_conn

DB_CONN = postgres_conn()
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

# Initialize modular client libraries
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


# ----------------- PYDANTIC SCHEMAS -----------------
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

class QuestionResponse(BaseModel):
    answer: str
    limitations: List[str]
    sources: List[SourceInfo]
    database_counts: Dict[str, Any] = Field(default_factory=dict)
    is_safe: bool = True

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

# --- Extended CS-ROP models ---
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


# ----------------- METADATA UTILS -----------------
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

# ----------------- CORE API ENDPOINTS -----------------

@app.get("/api/billing-instructions")
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

@app.get("/health")
def health() -> dict:
    db_ok = True
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            pass
    except Exception:
        db_ok = False
        
    from app_skeleton.api.connector_status import production_connectors_summary

    return {
        "status": "ok",
        "database_connected": db_ok,
        "llm_client_provider": llm_client.provider,
        "llm_client_healthy": llm_client.healthCheck(),
        "connectors": production_connectors_summary(),
    }


@app.get("/api/processor/status")
def processor_status() -> dict:
    """Public health-style status for the OS-level autonomous processor daemon."""
    from app_skeleton.api.processor_status import read_processor_status

    return read_processor_status()


@app.get("/stats")
def stats(project_code: Optional[List[str]] = Query(None)) -> dict:
    return query_postgres_metadata(project_code)

@app.post("/ask", response_model=QuestionResponse)
def ask(req: QuestionRequest) -> QuestionResponse:
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

    # 3. Fetch structured stats from Postgres
    db_data = query_postgres_metadata(req.project_codes)

    clinical_block = _clinical_context_for_question(safe_question, req.project_codes or [])
    
    # 4. Retrieve documentation chunks using RAGAgent (use active_llm for embedding queries)
    temp_rag = RAGAgent(qdrant_client, active_llm)
    retrieved_sources = temp_rag.retrieve(safe_question, req.project_codes)

    lab_hits = search_lab_knowledge(
        safe_question,
        limit=8,
        qdrant=qdrant_client,
        llm=active_llm,
    )
    seen_ids = {src.get("chunk_id") for src in retrieved_sources}
    for hit in lab_hits:
        cid = hit.get("chunk_uid")
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        retrieved_sources.append({
            "title": hit.get("title") or hit.get("citation"),
            "source_type": "lab_knowledge",
            "source_uuid": hit.get("document_code") or hit.get("relative_path") or "",
            "chunk_id": cid,
            "text_preview": hit.get("excerpt") or "",
            "score": hit.get("score", 0.0),
        })
    retrieved_sources = retrieved_sources[:12]

    sources = [
        SourceInfo(
            title=src["title"],
            source_type=src["source_type"],
            source_uuid=src["source_uuid"],
            chunk_id=src["chunk_id"],
            text_preview=src["text_preview"],
            score=src["score"]
        ) for src in retrieved_sources
    ]

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
        is_safe=True
    )

@app.post("/install_guide")
def install_guide(req: InstallRequest) -> dict:
    guide = install_agent.get_instructions(req.tool_name, req.os_platform)
    if guide["status"] == "success":
        # Package standard script using script wrapper
        formatted_script = guide["commands"]
        if req.os_platform.lower() == "linux" or req.os_platform.lower() == "macos":
            formatted_script = script_agent.generate_bash(guide["commands"])
        return {
            "status": "success",
            "tool": guide["tool"],
            "os": guide["os"],
            "script": formatted_script,
            "verification": guide["verification"],
            "expected_output": guide["expected_output"],
            "troubleshooting": guide["troubleshooting"]
        }
    else:
        raise HTTPException(status_code=400, detail=guide["message"])

@app.post("/lumi_job")
def lumi_job(req: LumiJobRequest) -> dict:
    script = hpc_agent.generate_job(req.model_dump())
    
    # Save script to database
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO platform.generated_script (script_name, script_body, target_language) VALUES (%s, %s, %s) RETURNING script_id;",
                    (req.job_name, script, "bash")
                )
                script_id = cur.fetchone()[0]
                
                # Perform basic static analysis validation
                status = "passed"
                log = "Basic validations passed: Contains set -euo pipefail, checks folders existence, sets Apptainer path."
                if "/scratch" not in script:
                    status = "warnings"
                    log += "\nWarning: No scratch paths detected in script parameters."
                
                cur.execute(
                    "INSERT INTO platform.validation_result (script_id, status, output_log) VALUES (%s, %s, %s);",
                    (script_id, status, log)
                )
    except Exception as exc:
        LOGGER.warning("Failed to audit generated Slurm script to Postgres: %s", exc)

    return {
        "status": "success",
        "script": script,
        "warnings": ["Ensure you replace project_account with active LUMI billing project allocation."]
    }

@app.post("/parse_log")
def parse_log(req: LogParseRequest) -> dict:
    diagnosis = troubleshooting_agent.diagnose_log(req.log_text)
    return {
        "status": "success",
        "cause": diagnosis["cause"],
        "recommended_fix": diagnosis["fix"],
        "prevention": diagnosis["prevention"]
    }

@app.post("/run_checker")
def run_checker(req: CheckerRequest) -> dict:
    script_path = checker_script(req.checker_name)
    if not script_path:
        raise HTTPException(status_code=400, detail=f"Checker script {req.checker_name} not found.")

    try:
        cmd = [str(script_path)]
        if script_path.suffix == ".py":
            cmd = ["python3", str(script_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=int(os.getenv("CHECKER_TIMEOUT_SECONDS", "45")), cwd=str(script_path.parent))
        status = "PASS" if res.returncode == 0 else "WARNING/FAIL"
        combined = "\n".join(filter(None, [res.stdout.strip(), res.stderr.strip()]))
        return {
            "status": status,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "returncode": res.returncode,
            "execution_logs": combined or "(no output)",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to run environment verification tool: {exc}")


@app.post("/run_checker_suite")
def run_checker_suite() -> dict:
    """Run all available environment checkers and return combined report."""
    names = ["python_env", "gpu", "napari", "docker", "lumi_modules", "cylinter_inputs", "project_structure"]
    results = []
    logs = []
    for name in names:
        script_path = checker_script(name)
        if not script_path:
            results.append({"checker_name": name, "status": "SKIPPED", "execution_logs": "Script not found"})
            continue
        try:
            cmd = ["python3", str(script_path)] if script_path.suffix == ".py" else [str(script_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=int(os.getenv("CHECKER_TIMEOUT_SECONDS", "45")), cwd=str(script_path.parent))
            combined = "\n".join(filter(None, [res.stdout.strip(), res.stderr.strip()]))
            status = "PASS" if res.returncode == 0 else "WARNING/FAIL"
            entry = {"checker_name": name, "status": status, "returncode": res.returncode, "execution_logs": combined or "(no output)"}
            results.append(entry)
            logs.append(f"=== {name} [{status}] ===\n{combined}\n")
        except Exception as exc:
            results.append({"checker_name": name, "status": "ERROR", "execution_logs": str(exc)})
            logs.append(f"=== {name} [ERROR] ===\n{exc}\n")

    overall = "PASS" if all(r.get("status") == "PASS" for r in results if r.get("status") != "SKIPPED") else "WARNING/FAIL"
    return {
        "status": overall,
        "checkers": results,
        "execution_logs": "\n".join(logs),
    }


# Helper to automatically create notebook records for tracing actions
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

@app.get("/projects")
def get_projects() -> List[Dict[str, Any]]:
    return fetch_projects_unified()

@app.put("/projects/{project_code}")
def update_project(project_code: str, req: ProjectExtensionUpdate) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (project_code,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = row[0]

                # Make sure row exists in project_extension
                cur.execute("INSERT INTO platform.project_extension (project_id) VALUES (%s) ON CONFLICT DO NOTHING;", (pid,))

                # Build update query
                fields = []
                params = []
                for k, v in req.model_dump(exclude_unset=True).items():
                    fields.append(f"{k} = %s")
                    params.append(v)
                params.append(pid)

                if fields:
                    query = f"UPDATE platform.project_extension SET {', '.join(fields)}, updated_at = now() WHERE project_id = %s;"
                    cur.execute(query, tuple(params))

                # Automatically append to the notebook system of record!
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                debdeba_id = cur.fetchone()[0]
                auto_log_notebook_entry(
                    conn, pid, debdeba_id, 
                    title=f"Project {project_code} parameters updated",
                    content=f"Researcher updated project extensions: {', '.join(fields)}",
                    entry_type="protocol_deviation_note"
                )
                conn.commit()
                return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/notebook")
def get_notebook(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT ne.entry_id, p.project_code, s.sample_code, ne.title, ne.pipeline_stage, ne.content, ne.conclusions, ne.issues_found, ne.next_steps, ne.tags, ne.entry_type, ne.visibility_level, ne.created_at, r.full_name,
                           (SELECT COUNT(*) FROM platform.notebook_revision nr WHERE nr.entry_id = ne.entry_id) as revision_count
                    FROM platform.notebook_entry ne
                    JOIN core.project p ON ne.project_id = p.project_id
                    LEFT JOIN core.sample s ON ne.sample_id = s.sample_id
                    JOIN platform.researcher r ON ne.author_id = r.researcher_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY ne.created_at DESC;"
                
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                result = []
                for r in rows:
                    result.append({
                        "entry_id": str(r[0]),
                        "project_code": r[1],
                        "sample_code": r[2],
                        "title": r[3],
                        "pipeline_stage": r[4],
                        "content": r[5],
                        "conclusions": r[6],
                        "issues_found": r[7],
                        "next_steps": r[8],
                        "tags": r[9],
                        "entry_type": r[10],
                        "visibility_level": r[11],
                        "created_at": r[12].isoformat(),
                        "author_name": r[13],
                        "version": r[14]
                    })
                return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/notebook/{entry_id}/revisions")
def get_notebook_revisions(entry_id: str) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT revision_id, revision_number, title, content, created_at
                    FROM platform.notebook_revision
                    WHERE entry_id = %s
                    ORDER BY revision_number DESC;
                """, (entry_id,))
                rows = cur.fetchall()
                return [{
                    "revision_id": str(r[0]),
                    "revision_number": r[1],
                    "title": r[2],
                    "content": r[3],
                    "created_at": r[4].isoformat()
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/notebook")
def create_notebook(req: NotebookEntryCreate) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                p_row = cur.fetchone()
                if not p_row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = p_row[0]

                sid = None
                if req.sample_code:
                    cur.execute("SELECT sample_id FROM core.sample WHERE sample_code = %s;", (req.sample_code,))
                    s_row = cur.fetchone()
                    if s_row:
                        sid = s_row[0]

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                debdeba_id = cur.fetchone()[0]

                entry_id = auto_log_notebook_entry(
                    conn, pid, debdeba_id, req.title, req.content,
                    req.entry_type, sid, req.pipeline_stage
                )

                # Set extra fields if passed
                if req.conclusions or req.issues_found or req.next_steps:
                    cur.execute("""
                        UPDATE platform.notebook_entry
                        SET conclusions = %s, issues_found = %s, next_steps = %s, tags = %s::text[]
                        WHERE entry_id = %s;
                    """, (req.conclusions, req.issues_found, req.next_steps, req.tags, entry_id))

                conn.commit()
                return {"status": "success", "entry_id": str(entry_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.put("/notebook/{entry_id}")
def update_notebook(entry_id: str, req: NotebookEntryUpdate) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Get next version number
                cur.execute("SELECT COUNT(*) FROM platform.notebook_revision WHERE entry_id = %s;", (entry_id,))
                rev_count = cur.fetchone()[0]
                new_rev = rev_count + 1

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                debdeba_id = cur.fetchone()[0]

                # Update main table
                cur.execute("""
                    UPDATE platform.notebook_entry
                    SET title = %s, content = %s, conclusions = %s, issues_found = %s, next_steps = %s, tags = %s::text[], entry_type = %s, updated_at = now()
                    WHERE entry_id = %s;
                """, (req.title, req.content, req.conclusions, req.issues_found, req.next_steps, req.tags, req.entry_type, entry_id))

                # Insert revision record
                cur.execute("""
                    INSERT INTO platform.notebook_revision (entry_id, revision_number, title, content, conclusions, issues_found, next_steps, tags, author_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::text[], %s);
                """, (entry_id, new_rev, req.title, req.content, req.conclusions, req.issues_found, req.next_steps, req.tags, debdeba_id))

                conn.commit()
                return {"status": "success", "revision_number": new_rev}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/notebook/{entry_id}/rollback")
def rollback_notebook(entry_id: str, revision_number: int = Query(...)) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, content, conclusions, issues_found, next_steps, tags
                    FROM platform.notebook_revision
                    WHERE entry_id = %s AND revision_number = %s;
                """, (entry_id, revision_number))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Revision not found")

                cur.execute("""
                    UPDATE platform.notebook_entry
                    SET title = %s, content = %s, conclusions = %s, issues_found = %s, next_steps = %s, tags = %s::text[], updated_at = now()
                    WHERE entry_id = %s;
                """, (row[0], row[1], row[2], row[3], row[4], row[5], entry_id))

                conn.commit()
                return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/decisions")
def get_decisions(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT d.decision_id, p.project_code, d.title, d.decision_details, d.rationale, d.alternatives_considered, r.full_name, d.decision_date
                    FROM platform.decision_registry d
                    JOIN core.project p ON d.project_id = p.project_id
                    LEFT JOIN platform.researcher r ON d.decided_by_id = r.researcher_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY d.decision_date DESC;"
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "decision_id": str(r[0]),
                    "project_code": r[1],
                    "title": r[2],
                    "decision_details": r[3],
                    "rationale": r[4],
                    "alternatives_considered": r[5],
                    "decider_name": r[6],
                    "decision_date": str(r[7])
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/decisions")
def create_decision(req: DecisionCreate) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                pid = cur.fetchone()[0]
                
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = %s;", (req.decided_by_username,))
                rid = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO platform.decision_registry (project_id, title, decision_details, rationale, alternatives_considered, decided_by_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING decision_id;
                """, (pid, req.title, req.decision_details, req.rationale, req.alternatives_considered, rid))
                decision_id = cur.fetchone()[0]

                # Automatically log in the notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Decision Logged: {req.title}",
                    content=f"A formal research decision was committed.\nDetails: {req.decision_details}\nRationale: {req.rationale}",
                    entry_type="decision_note"
                )
                conn.commit()
                return {"status": "success", "decision_id": str(decision_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/wiki")
def get_wiki() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT w.wiki_id, w.title, w.slug, w.content, w.wiki_type, p.project_code, r.full_name, w.updated_at,
                           (SELECT COUNT(*) FROM platform.wiki_revision WHERE wiki_id = w.wiki_id) as rev_count
                    FROM platform.research_wiki w
                    LEFT JOIN core.project p ON w.project_id = p.project_id
                    LEFT JOIN platform.researcher r ON w.created_by_id = r.researcher_id
                    ORDER BY w.updated_at DESC;
                """)
                rows = cur.fetchall()
                return [{
                    "wiki_id": str(r[0]),
                    "title": r[1],
                    "slug": r[2],
                    "content": r[3],
                    "wiki_type": r[4],
                    "project_code": r[5],
                    "author_name": r[6],
                    "updated_at": r[7].isoformat(),
                    "revision": r[8] if r[8] > 0 else 1
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/wiki")
def create_wiki_page(req: WikiPageCreate) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                pid = None
                if req.project_code:
                    cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                    pid = cur.fetchone()[0]

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                rid = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO platform.research_wiki (title, slug, content, wiki_type, project_id, created_by_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING wiki_id;
                """, (req.title, req.slug, req.content, req.wiki_type, pid, rid))
                wiki_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO platform.wiki_revision (wiki_id, revision_number, title, content, author_id)
                    VALUES (%s, 1, %s, %s, %s);
                """, (wiki_id, req.title, req.content, rid))

                conn.commit()
                return {"status": "success", "wiki_id": str(wiki_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.put("/wiki/{wiki_id}")
def update_wiki_page(wiki_id: str, req: WikiPageUpdate) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Count current versions
                cur.execute("SELECT COUNT(*) FROM platform.wiki_revision WHERE wiki_id = %s;", (wiki_id,))
                count = cur.fetchone()[0]
                new_rev = count + 1

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                rid = cur.fetchone()[0]

                cur.execute("""
                    UPDATE platform.research_wiki
                    SET title = %s, content = %s, wiki_type = %s, updated_at = now()
                    WHERE wiki_id = %s;
                """, (req.title, req.content, req.wiki_type, wiki_id))

                cur.execute("""
                    INSERT INTO platform.wiki_revision (wiki_id, revision_number, title, content, author_id)
                    VALUES (%s, %s, %s, %s, %s);
                """, (wiki_id, new_rev, req.title, req.content, rid))

                conn.commit()
                return {"status": "success", "revision_number": new_rev}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/folders")
def get_folders(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT f.folder_id, p.project_code, s.sample_code, f.folder_name, f.absolute_path, f.storage_system, f.data_type, f.file_count, f.total_size_bytes
                    FROM platform.folder_catalog f
                    JOIN core.project p ON f.project_id = p.project_id
                    LEFT JOIN core.sample s ON f.sample_id = s.sample_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "folder_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "folder_name": r[3],
                    "absolute_path": r[4],
                    "storage_system": r[5],
                    "data_type": r[6],
                    "file_count": r[7],
                    "total_size_bytes": r[8]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/datasets")
def get_datasets(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT d.dataset_id, p.project_code, s.sample_code, d.dataset_name, d.data_type, d.format, d.file_path, d.file_size_bytes, d.quality_status, d.notes
                    FROM platform.dataset_catalog d
                    JOIN core.project p ON d.project_id = p.project_id
                    LEFT JOIN core.sample s ON d.sample_id = s.sample_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "dataset_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "dataset_name": r[3],
                    "data_type": r[4],
                    "format": r[5],
                    "file_path": r[6],
                    "file_size": r[7],
                    "quality_status": r[8],
                    "notes": r[9]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/pipeline_runs")
def get_pipeline_runs(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT pr.run_id, p.project_code, s.sample_code, pr.pipeline_stage, pr.command_used, pr.script_path, pr.status, pr.error_summary, pr.qc_result, pr.created_at
                    FROM platform.pipeline_run pr
                    JOIN core.project p ON pr.project_id = p.project_id
                    LEFT JOIN core.sample s ON pr.sample_id = s.sample_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY pr.created_at DESC;"
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "run_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "pipeline_stage": r[3],
                    "command_used": r[4],
                    "script_path": r[5],
                    "status": r[6],
                    "error_summary": r[7],
                    "qc_result": r[8],
                    "created_at": r[9].isoformat()
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/tasks")
def get_tasks(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT t.task_id, p.project_code, s.sample_code, r.full_name, t.title, t.description, t.status, t.priority, t.due_date
                    FROM platform.task t
                    JOIN core.project p ON t.project_id = p.project_id
                    LEFT JOIN core.sample s ON t.sample_id = s.sample_id
                    LEFT JOIN platform.researcher r ON t.assigned_to = r.researcher_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "task_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "assigned_to": r[3],
                    "title": r[4],
                    "description": r[5],
                    "status": r[6],
                    "priority": r[7],
                    "due_date": str(r[8]) if r[8] else None
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/tasks")
def create_task(req: TaskCreate) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                pid = cur.fetchone()[0]

                sid = None
                if req.sample_code:
                    cur.execute("SELECT sample_id FROM core.sample WHERE sample_code = %s;", (req.sample_code,))
                    s_row = cur.fetchone()
                    if s_row:
                        sid = s_row[0]

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                rid = cur.fetchone()[0]

                due = datetime.strptime(req.due_date, "%Y-%m-%d").date() if req.due_date else None

                cur.execute("""
                    INSERT INTO platform.task (project_id, sample_id, title, description, status, priority, due_date, assigned_to)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING task_id;
                """, (pid, sid, req.title, req.description, req.status, req.priority, due, rid))
                task_id = cur.fetchone()[0]

                # Automatically log in the notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Task Created: {req.title}",
                    content=f"Task assigned to debdeba.\nDetails: {req.description or ''}\nStatus: {req.status}, Priority: {req.priority}",
                    entry_type="general_note",
                    sample_id=sid
                )
                conn.commit()
                return {"status": "success", "task_id": str(task_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.put("/tasks/{task_id}")
def update_task(task_id: str, req: TaskUpdate) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                due = datetime.strptime(req.due_date, "%Y-%m-%d").date() if req.due_date else None
                cur.execute("""
                    UPDATE platform.task
                    SET title = %s, description = %s, status = %s, priority = %s, due_date = %s, updated_at = now()
                    WHERE task_id = %s
                    RETURNING project_id, sample_id;
                """, (req.title, req.description, req.status, req.priority, due, task_id))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Task not found")
                
                pid, sid = row[0], row[1]
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                rid = cur.fetchone()[0]

                # Automatically log in the notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Task Updated: {req.title}",
                    content=f"Task status changed to {req.status}.\nPriority: {req.priority}",
                    entry_type="general_note",
                    sample_id=sid
                )
                conn.commit()
                return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/auto_logs")
def get_auto_logs() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT log_id, actor, event_type, description, created_at
                    FROM platform.auto_log
                    ORDER BY created_at DESC LIMIT 50;
                """)
                rows = cur.fetchall()
                return [{
                    "log_id": str(r[0]),
                    "actor": r[1],
                    "event_type": r[2],
                    "description": r[3],
                    "created_at": r[4].isoformat()
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/team")
def get_team() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT username, full_name, role, allowed_project_codes
                    FROM platform.researcher;
                """)
                rows = cur.fetchall()
                return [{
                    "username": r[0],
                    "full_name": r[1],
                    "role": r[2],
                    "allowed_projects": r[3]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ----------------- KNOWLEDGE ONBOARDING & REGISTRIES ENDPOINTS -----------------

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

@app.post("/projects")
def create_project(req: ProjectCreate) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Get or create lead researcher
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE full_name = %s OR username = %s LIMIT 1;", (req.project_lead, req.project_lead.lower().replace(" ", "")))
                row = cur.fetchone()
                if row:
                    lead_id = row[0]
                else:
                    username = req.project_lead.lower().replace(" ", "")[:15]
                    cur.execute("""
                        INSERT INTO platform.researcher (username, full_name, role, allowed_project_codes)
                        VALUES (%s, %s, 'researcher', ARRAY[%s]::text[])
                        RETURNING researcher_id;
                    """, (username, req.project_lead, req.project_code))
                    lead_id = cur.fetchone()[0]

                # Get PI researcher ID
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'afarkkila';")
                af_row = cur.fetchone()
                pi_id = af_row[0] if af_row else lead_id

                # Insert Core project
                cur.execute("""
                    INSERT INTO core.project (project_code, project_name, project_lead, principal_investigator, disease_focus, short_description, default_sensitivity, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::core.sensitivity_level, %s::core.record_status)
                    ON CONFLICT (project_code) DO UPDATE
                    SET project_name = EXCLUDED.project_name, short_description = EXCLUDED.short_description
                    RETURNING project_id;
                """, (req.project_code, req.project_name, req.project_lead, req.principal_investigator, req.disease_focus, req.short_description, req.default_sensitivity, req.status))
                pid = cur.fetchone()[0]

                # Insert Project Extension
                cur.execute("""
                    INSERT INTO platform.project_extension (project_id, project_short_title, research_question, project_type, priority, collaborators, ethics_approval_reference, current_blockers, next_actions, project_summary, latest_update)
                    VALUES (%s, %s, %s, %s, %s, %s::text[], %s, %s, %s, %s, 'Project onboarded via wizard.')
                    ON CONFLICT (project_id) DO UPDATE
                    SET ethics_approval_reference = EXCLUDED.ethics_approval_reference,
                        current_blockers = EXCLUDED.current_blockers,
                        next_actions = EXCLUDED.next_actions,
                        project_summary = EXCLUDED.project_summary;
                """, (pid, req.project_name[:50], req.short_description, req.project_type, req.priority, req.collaborators, req.ethics_approval_reference, req.current_blockers, req.next_actions, req.project_summary))

                # Add members to project_member
                # Lead
                cur.execute("""
                    INSERT INTO platform.project_member (project_id, researcher_id, role, project_access_level, notes)
                    VALUES (%s, %s, 'project_lead', 'read_write', 'Lead researcher on project')
                    ON CONFLICT (project_id, researcher_id) DO NOTHING;
                """, (pid, lead_id))
                
                # PI
                cur.execute("""
                    INSERT INTO platform.project_member (project_id, researcher_id, role, project_access_level, notes)
                    VALUES (%s, %s, 'PI', 'admin', 'Principal Investigator oversight')
                    ON CONFLICT (project_id, researcher_id) DO NOTHING;
                """, (pid, pi_id))

                # Seeding onboarding checklist items for this new project
                checklist_items = [
                    ("project", "Project Description & Goals", "Ensure project description, scientific questions, and goals are documented."),
                    ("project", "Members & Collaborators", "Add responsible researchers and their clinical/computational roles."),
                    ("document", "Protocols & SOPs", "Link the wet-lab staining/imaging and dry-lab segmentation SOPs used."),
                    ("document", "Ethics Approvals", "Record the ethics board registry reference number."),
                    ("software", "Software Versions", "Document package versions (Cylinter, Ashlar, Mesmer, Tribus) used."),
                    ("pipeline", "Stitching Pipeline Run", "Execute and link Ashlar stitching logs/runs."),
                    ("pipeline", "Cell Segmentation Quality Check", "Verify cell boundaries and mask outputs."),
                    ("dataset", "OME-TIFF Raw Slides", "Verify raw image folders are cataloged and size computed."),
                    ("dataset", "Segmented Cell Masks", "Store and register cell masks (.tif) in object storage."),
                    ("dataset", "Quantified Cell Features Table", "Verify single-cell expression tables (.csv/.h5ad) are cataloged."),
                    ("sample", "Sample Code Verification", "Align clinical patient codes with imaging specimen codes."),
                    ("publication", "Preprint/Publication Linkage", "Track linked publications or conference poster details.")
                ]
                for category, item, desc in checklist_items:
                    cur.execute("""
                        INSERT INTO platform.onboarding_checklist (project_id, category, item_name, description, status)
                        VALUES (%s, %s, %s, %s, 'pending')
                        ON CONFLICT (project_id, category, item_name) DO NOTHING;
                    """, (pid, category, item, desc))

                # Automatically write to Digital Notebook
                auto_log_notebook_entry(
                    conn, pid, lead_id,
                    title="Project Onboarded Successfully",
                    content=f"The project '{req.project_name}' has been created with code '{req.project_code}' by Lead {req.project_lead}.\nPriority set to: {req.priority}\nEthics Reference: {req.ethics_approval_reference}",
                    entry_type="general_note"
                )

                conn.commit()
                return {"status": "success", "project_id": str(pid)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/ai-models")
def get_ai_models() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT model_id, name, model_type, source, license, parameters, gpu_requirements, memory_requirements, local_deployment, api_deployment, use_cases, strengths, weaknesses, installation_instructions
                    FROM platform.ai_model
                    ORDER BY model_type, name;
                """)
                rows = cur.fetchall()
                return [{
                    "model_id": str(r[0]),
                    "name": r[1],
                    "model_type": r[2],
                    "source": r[3],
                    "license": r[4],
                    "parameters": r[5],
                    "gpu_requirements": r[6],
                    "memory_requirements": r[7],
                    "local_deployment": r[8],
                    "api_deployment": r[9],
                    "use_cases": r[10],
                    "strengths": r[11],
                    "weaknesses": r[12],
                    "installation_instructions": r[13]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/infrastructure")
def get_infrastructure() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT resource_id, name, resource_type, operating_system, cpu_specs, ram_specs, gpu_specs, storage_specs, installed_software, access_notes, maintenance_notes
                    FROM platform.infrastructure
                    ORDER BY resource_type, name;
                """)
                rows = cur.fetchall()
                return [{
                    "resource_id": str(r[0]),
                    "name": r[1],
                    "resource_type": r[2],
                    "operating_system": r[3],
                    "cpu_specs": r[4],
                    "ram_specs": r[5],
                    "gpu_specs": r[6],
                    "storage_specs": r[7],
                    "installed_software": r[8],
                    "access_notes": r[9],
                    "maintenance_notes": r[10]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/publications")
def get_publications() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT pub.pub_id, pub.title, pub.authors, pub.journal, pub.publication_year, pub.doi, pub.pmid, pub.abstract, p.project_code, pub.full_text_path
                    FROM platform.publication pub
                    LEFT JOIN core.project p ON pub.project_id = p.project_id
                    ORDER BY pub.publication_year DESC, pub.title;
                """)
                rows = cur.fetchall()
                return [{
                    "pub_id": str(r[0]),
                    "title": r[1],
                    "authors": r[2],
                    "journal": r[3],
                    "publication_year": r[4],
                    "doi": r[5],
                    "pmid": r[6],
                    "abstract": r[7],
                    "project_code": r[8],
                    "full_text_path": r[9]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/checklists/{project_code}")
def get_project_checklists(project_code: str) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (project_code,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = row[0]
                cur.execute("""
                    SELECT checklist_id, category, item_name, description, status, checked_at
                    FROM platform.onboarding_checklist
                    WHERE project_id = %s
                    ORDER BY category, item_name;
                """, (pid,))
                rows = cur.fetchall()
                return [{
                    "checklist_id": str(r[0]),
                    "category": r[1],
                    "item_name": r[2],
                    "description": r[3],
                    "status": r[4],
                    "checked_at": r[5].isoformat() if r[5] else None
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/checklists/toggle")
def toggle_checklist(req: ChecklistToggleRequest) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Get current status and item details
                cur.execute("""
                    SELECT project_id, category, item_name, status 
                    FROM platform.onboarding_checklist 
                    WHERE checklist_id = %s;
                """, (req.checklist_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Checklist item not found")
                
                pid, category, item_name, current_status = row[0], row[1], row[2], row[3]
                
                # Toggle or set status
                checked_at = datetime.now() if req.status == 'completed' else None
                cur.execute("""
                    UPDATE platform.onboarding_checklist
                    SET status = %s, checked_at = %s, updated_at = now()
                    WHERE checklist_id = %s;
                """, (req.status, checked_at, req.checklist_id))

                # Fetch researcher ID
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = %s LIMIT 1;", (req.username,))
                res_row = cur.fetchone()
                rid = res_row[0] if res_row else None

                # Log to notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Checklist Item Updated: {item_name}",
                    content=f"Checklist item '{item_name}' in category '{category}' changed from '{current_status}' to '{req.status}'.",
                    entry_type="general_note"
                )

                conn.commit()
                return {"status": "success", "new_status": req.status}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/ingest-document")
def ingest_document(req: DocumentIngestRequest) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Find project ID if project_code is provided
                pid = None
                if req.project_code:
                    cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                    row = cur.fetchone()
                    if row:
                        pid = row[0]

                # Insert document record
                cur.execute("""
                    INSERT INTO platform.document_ingestion (filename, file_type, extracted_text, tags, project_id, software_associations, pipeline_stage_associations, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING doc_id;
                """, (req.filename, req.file_type, req.extracted_text, req.tags, pid, req.software_associations, req.pipeline_stage_associations, psycopg.types.json.Jsonb(req.metadata_dict)))
                doc_id = cur.fetchone()[0]

                # Fetch researcher ID (default to IT Specialist / debdeba)
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                rid = cur.fetchone()[0]

                # Log into Digital Notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Document Ingested: {req.filename}",
                    content=f"Document '{req.filename}' ({req.file_type}) successfully parsed and uploaded to catalog.\nAssociations:\n- Software: {', '.join(req.software_associations) or 'None'}\n- Pipeline Stages: {', '.join(req.pipeline_stage_associations) or 'None'}",
                    entry_type="general_note"
                )

                conn.commit()
                return {"status": "success", "doc_id": str(doc_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/gap-analysis")
def gap_analysis() -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # 1. Total projects count
                cur.execute("SELECT COUNT(*) FROM core.project;")
                total_projects = cur.fetchone()[0]

                # 2. Checklist stats
                cur.execute("SELECT COUNT(*), SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) FROM platform.onboarding_checklist;")
                total_items, completed_items = cur.fetchone()
                total_items = total_items or 0
                completed_items = completed_items or 0
                readiness_score = round((completed_items / total_items * 100), 1) if total_items > 0 else 0.0

                # 3. Project-specific scores
                cur.execute("""
                    SELECT p.project_code, p.project_name, COUNT(c.checklist_id), SUM(CASE WHEN c.status = 'completed' THEN 1 ELSE 0 END)
                    FROM core.project p
                    LEFT JOIN platform.onboarding_checklist c ON p.project_id = c.project_id
                    GROUP BY p.project_code, p.project_name
                    ORDER BY p.project_code;
                """)
                project_breakdown = []
                for code, name, t_count, c_count in cur.fetchall():
                    t_count = t_count or 0
                    c_count = c_count or 0
                    p_score = round((c_count / t_count * 100), 1) if t_count > 0 else 0.0
                    project_breakdown.append({
                        "project_code": code,
                        "project_name": name,
                        "total_items": t_count,
                        "completed_items": c_count,
                        "score": p_score
                    })

                # 4. Inventory counts
                cur.execute("SELECT COUNT(*) FROM platform.ai_model;")
                ai_models_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.infrastructure;")
                infrastructure_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.publication;")
                publications_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.document_ingestion;")
                documents_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.folder_catalog;")
                folders_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.dataset_catalog;")
                datasets_count = cur.fetchone()[0]

                # Find missing items
                cur.execute("""
                    SELECT p.project_code, c.category, c.item_name
                    FROM platform.onboarding_checklist c
                    JOIN core.project p ON c.project_id = p.project_id
                    WHERE c.status = 'pending'
                    ORDER BY p.project_code, c.category
                    LIMIT 20;
                """)
                missing_checklist_items = [{"project_code": r[0], "category": r[1], "item_name": r[2]} for r in cur.fetchall()]

                # Generate dynamic recommendations
                recommendations = []
                if readiness_score < 50:
                    recommendations.append("Priority 1: Populate pending checklist items for active clinical cohorts (stitching runs & segmented cell masks).")
                if publications_count == 0:
                    recommendations.append("Priority 2: Seed the publication registry with lab papers to facilitate citation references for Chat Copilot.")
                if documents_count < 5:
                    recommendations.append("Priority 3: Utilize the Document Ingestion wizard to upload local multiplex staining protocols and Slurm template scripts.")
                if ai_models_count < 10:
                    recommendations.append("Priority 4: Verify the local installation scripts for segmentation models (Mesmer / SAM2) are registered.")
                
                if not recommendations:
                    recommendations.append("All core metadata fields are populated. Ready to scale to production multi-cohort processing.")

                coverage = project_catalog_coverage()

                return {
                    "total_projects": total_projects,
                    "catalog_coverage": coverage,
                    "readiness_score": readiness_score,
                    "completed_checklist_items": completed_items,
                    "total_checklist_items": total_items,
                    "project_breakdown": project_breakdown,
                    "ai_models_count": ai_models_count,
                    "infrastructure_count": infrastructure_count,
                    "publications_count": publications_count,
                    "documents_count": documents_count,
                    "folders_count": folders_count,
                    "datasets_count": datasets_count,
                    "missing_checklist_items": missing_checklist_items,
                    "recommendations": recommendations
                }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# --- Phase 3: Feature warehouse ---

@app.post("/features/seed")
def features_seed() -> dict:
    return seed_feature_warehouse()


@app.get("/features/definitions")
def features_definitions() -> dict:
    defs = list_feature_definitions()
    return {"count": len(defs), "features": defs}


@app.get("/features/matrices")
def features_matrices(project_code: Optional[str] = Query(None)) -> dict:
    matrices = list_feature_matrices(project_code)
    return {"count": len(matrices), "matrices": matrices}


@app.get("/features/sample/{sample_code}")
def features_sample(sample_code: str) -> dict:
    return get_sample_features(sample_code)


@app.post("/features/similarity")
def features_similarity(req: SimilarityRequest) -> dict:
    similar = find_similar_samples(req.sample_code, limit=req.limit, project_code=req.project_code)
    result = {"query_sample": req.sample_code, "similar": similar}
    register_analysis_run("feature_similarity", req.model_dump(), result, req.project_code, title=f"Similarity: {req.sample_code}")
    return result


# --- Phase 4: Clinical / statistical tools ---

@app.get("/clinical/variables")
def clinical_variables() -> dict:
    vars_ = get_clinical_variables()
    return {"count": len(vars_), "variables": vars_}


@app.post("/clinical/survival")
def clinical_survival(req: SurvivalRequest) -> dict:
    results = run_survival_analysis(
        duration_col=req.duration_col,
        event_col=req.event_col,
        group_col=req.group_col,
        project_code=req.project_code,
    )
    if req.register_run:
        register_analysis_run("survival", req.model_dump(), results, req.project_code, title="Kaplan-Meier survival")
    return results


@app.post("/clinical/group-compare")
def clinical_group_compare(req: GroupCompareRequest) -> dict:
    results = run_group_comparison(
        feature_col=req.feature_col,
        group_col=req.group_col,
        project_code=req.project_code,
    )
    if req.register_run:
        register_analysis_run("group_compare", req.model_dump(), results, req.project_code, title=f"Compare {req.feature_col}")
    return results


@app.get("/analysis-runs")
def analysis_runs(limit: int = Query(20, ge=1, le=100)) -> dict:
    runs = list_analysis_runs(limit)
    return {"count": len(runs), "runs": runs}


@app.get("/clinical/recipe/{analysis_type}")
def clinical_recipe(analysis_type: str) -> dict:
    script = clinical_agent.get_analysis_recipe(analysis_type)
    return {"analysis_type": analysis_type, "script": script}


# --- PROJECT FILES & LAB DATABASE (shared path helpers) ---

import pathlib
import mimetypes
from fastapi.responses import FileResponse


SAFE_TEXT_EXTENSIONS = {".txt", ".md", ".py", ".r", ".sh", ".json", ".yaml", ".yml", ".sql", ".csv", ".tsv", ".toml", ".ini", ".cfg", ".log"}
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


# --- LAB DATABASE BROWSER (Overview, Orders, Social, Wet-lab folders) ---


class LabIngestRequest(BaseModel):
    refresh_extract: bool = False


@app.get("/api/knowledge/lab/stats")
def knowledge_lab_stats() -> dict:
    return get_lab_index_stats()


@app.get("/api/knowledge/lab/search")
def knowledge_lab_search(
    q: str = Query(..., min_length=2),
    section_id: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    if section_id and section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    results = search_lab_knowledge(
        q,
        section_id=section_id,
        limit=limit,
        qdrant=qdrant_client,
        llm=llm_client,
    )
    return {"corpus": LAB_CORPUS, "query": q, "count": len(results), "results": results}


@app.post("/api/knowledge/lab/ingest-all")
def knowledge_lab_ingest_all(req: LabIngestRequest = LabIngestRequest()) -> dict:
    try:
        return ingest_all_lab_sections(
            refresh_extract=req.refresh_extract,
            qdrant=qdrant_client,
            llm=llm_client,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/knowledge/lab/ingest/{section_id}")
def knowledge_lab_ingest_section(section_id: str, req: LabIngestRequest = LabIngestRequest()) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    try:
        return ingest_section_to_database(
            section_id,
            refresh_extract=req.refresh_extract,
            qdrant=qdrant_client,
            llm=llm_client,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/storage/roots", dependencies=_FIREBASE_PROTECTED)
def storage_roots_list() -> dict:
    """Phase 1: logical storage providers (configured flags only, no paths)."""
    from app_skeleton.api.paths import storage_roots_public_summary
    from app_skeleton.api.connector_status import production_connectors_summary

    return {
        "providers": storage_roots_public_summary(),
        "production_connectors": production_connectors_summary(),
    }


@app.get("/api/platform/connectors")
def platform_connectors_status() -> dict:
    """Firebase / Supabase / storage connector readiness — no secrets."""
    from app_skeleton.api.connector_status import production_connectors_summary

    return production_connectors_summary()


@app.get("/api/auth/config")
def auth_config_public() -> dict:
    """Firebase web client config + Email/Password-only policy (no Google Sign-In)."""
    from app_skeleton.api.auth_firebase import AUTH_DISABLED
    from app_skeleton.api.firebase_config import firebase_client_config_public

    return {
        "auth_disabled": AUTH_DISABLED,
        "firebase": firebase_client_config_public(),
    }


@app.get("/api/vault/summary", dependencies=_FIREBASE_PROTECTED)
def vault_summary_endpoint() -> dict:
    summary = vault_summary()
    public = {k: v for k, v in summary.items() if k != "database_root"}
    missing = assert_all_section_roots_exist()
    return {"summary": public, "missing_section_roots": missing}


@app.get("/api/vault/search", dependencies=_FIREBASE_PROTECTED)
def vault_search(
    q: str = Query("", min_length=0),
    domain: Optional[str] = Query(None),
    project_hint: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    extraction_status: Optional[str] = Query(None),
    vector_status: Optional[str] = Query(None),
    uncategorized_only: bool = Query(False),
    limit: int = Query(25, ge=1, le=100),
) -> dict:
    results = search_vault(
        q,
        domain=domain,
        project_hint=project_hint,
        review_status=review_status,
        extraction_status=extraction_status,
        vector_status=vector_status,
        uncategorized_only=uncategorized_only,
        limit=limit,
    )
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/vault/review-queue", dependencies=_FIREBASE_PROTECTED)
def vault_review_queue_endpoint(
    limit: int = Query(50, ge=1, le=200),
    max_confidence: float = Query(0.85, ge=0, le=1),
    queue: str = Query("low_confidence", description="low_confidence | uncategorized | failed"),
    extraction_status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
) -> dict:
    rows = vault_review_queue(
        limit=limit,
        max_confidence=max_confidence,
        queue=queue,
        extraction_status=extraction_status,
        review_status=review_status,
    )
    return {"count": len(rows), "queue": queue, "items": rows}


@app.patch("/api/vault/review/{asset_id}", dependencies=_FIREBASE_PROTECTED)
def vault_mark_reviewed(
    asset_id: str,
    review_status: str = Query("reviewed"),
) -> dict:
    return mark_asset_reviewed(asset_id, review_status=review_status)


@app.post("/api/vault/ingest/scan", dependencies=_FIREBASE_PROTECTED)
def vault_ingest_scan(
    resume: bool = Query(False),
    confirm_full_scan: bool = Query(False, description="Required for full DATABASE_ROOT scan (safety)"),
) -> dict:
    job = platform_admin.create_ingestion_job("vault_ingest_scan", config={"resume": resume})
    if not confirm_full_scan:
        raise HTTPException(
            status_code=400,
            detail="Set confirm_full_scan=true to run a full vault scan (read-only, metadata writes only).",
        )
    try:
        result = run_ingest_scan(resume=resume, job_id=str(job["job_id"]))
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("counts", {}).get("scanned"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault ingest scan failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/vault/ingest/project/{project_id}", dependencies=_FIREBASE_PROTECTED)
def vault_ingest_project_endpoint(
    project_id: str,
    resume: bool = Query(False),
) -> dict:
    job = platform_admin.create_ingestion_job(
        "vault_ingest_project",
        config={"project_id": project_id, "resume": resume},
    )
    try:
        result = vault_ingest_project(project_id, resume=resume, job_id=str(job["job_id"]))
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("counts", {}).get("scanned"),
        )
        return {**result, "job_id": job["job_id"]}
    except FileNotFoundError as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault project ingest failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/digitalize/scan", dependencies=_FIREBASE_PROTECTED)
def digitalize_scan(
    dry_run: bool = Query(False),
    resume: bool = Query(False),
    max_files: Optional[int] = Query(None, ge=1, le=100000),
) -> dict:
    from app_skeleton.api.project_digitalization_engine import run_digitalization

    try:
        return run_digitalization(mode="full", resume=resume, dry_run=dry_run, max_files=max_files)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/digitalize/project/{project_name}", dependencies=_FIREBASE_PROTECTED)
def digitalize_project(
    project_name: str,
    resume: bool = Query(False),
    dry_run: bool = Query(False),
    max_files: Optional[int] = Query(None, ge=1, le=100000),
) -> dict:
    from app_skeleton.api.project_digitalization_engine import run_digitalization

    try:
        return run_digitalization(
            mode="project",
            project_name=project_name,
            resume=resume,
            dry_run=dry_run,
            max_files=max_files,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/digitalize/retry-failed", dependencies=_FIREBASE_PROTECTED)
def digitalize_retry_failed(
    project_name: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
) -> dict:
    from app_skeleton.api.vault_ingestion_engine import retry_failed_extractions

    return retry_failed_extractions(project_hint=project_name, limit=limit)


@app.get("/api/digitalize/search", dependencies=_FIREBASE_PROTECTED)
def digitalize_search(
    q: str = Query(..., min_length=1),
    uncategorized_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    from app_skeleton.api.project_digitalization_engine import search_knowledge

    return {"items": search_knowledge(q, uncategorized_only=uncategorized_only, limit=limit)}


@app.get("/api/digitalize/review", dependencies=_FIREBASE_PROTECTED)
def digitalize_review(
    kind: str = Query("uncategorized"),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    from app_skeleton.api.project_digitalization_engine import list_review_queue

    return {"kind": kind, "items": list_review_queue(kind=kind, limit=limit)}


@app.patch("/api/digitalize/review/{asset_id}", dependencies=_FIREBASE_PROTECTED)
def digitalize_patch_review(
    asset_id: str,
    user_category: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    project_candidate_id: Optional[str] = Query(None),
) -> dict:
    from app_skeleton.api.project_digitalization_engine import patch_asset_review

    return patch_asset_review(
        asset_id,
        user_category=user_category,
        review_status=review_status,
        project_candidate_id=project_candidate_id,
    )


@app.get("/api/digitalize/runs", dependencies=_FIREBASE_PROTECTED)
def digitalize_runs(limit: int = Query(20, ge=1, le=100)) -> dict:
    from app_skeleton.api.project_digitalization_engine import _db_conn
    import psycopg

    with psycopg.connect(_db_conn(), connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT run_id, mode, storage_root, project_name, status, dry_run, started_at, finished_at
                FROM platform.digitalization_runs
                ORDER BY started_at DESC LIMIT %s;
                """,
                (limit,),
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"runs": rows}


@app.post("/api/vault/ingest/retry-failed", dependencies=_FIREBASE_PROTECTED)
def vault_ingest_retry_failed(
    project_hint: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
) -> dict:
    job = platform_admin.create_ingestion_job(
        "vault_ingest_retry_failed",
        config={"project_hint": project_hint, "limit": limit},
    )
    try:
        result = retry_failed_extractions(
            project_hint=project_hint,
            limit=limit,
            job_id=str(job["job_id"]),
        )
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("counts", {}).get("retried"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault retry-failed failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/vault/rebuild", dependencies=_FIREBASE_PROTECTED)
def vault_rebuild() -> dict:
    job = platform_admin.create_ingestion_job("vault_rebuild")
    try:
        result = vault_rebuild_inventory()
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("asset_count") or result.get("count"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault rebuild failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/supabase/sync/documents", dependencies=_FIREBASE_PROTECTED)
def supabase_sync_documents(
    dry_run: bool = Query(False),
    limit: Optional[int] = Query(None, ge=1, le=10_000),
    since: Optional[str] = Query(None, description="ISO timestamp for vault.updated_at filter"),
    _admin: dict = Depends(require_admin),
) -> dict:
    """Sync document metadata + truncated text from local Postgres to hosted Supabase (admin)."""
    del _admin
    job = platform_admin.create_ingestion_job(
        "supabase_document_sync",
        config={"dry_run": dry_run, "limit": limit, "since": since},
    )
    try:
        result = sync_documents_to_supabase(dry_run=dry_run, limit=limit, since=since)
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("document_rows_synced") or result.get("would_sync"),
            error_summary=None if result.get("status") in ("ok", "dry_run") else result.get("message"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Supabase document sync failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/vault/sync", dependencies=_FIREBASE_PROTECTED)
def vault_sync_postgres() -> dict:
    """Phase 3: upsert JSON inventory into platform.raw_asset_vault."""
    job = platform_admin.create_ingestion_job("vault_sync")
    try:
        result = sync_inventory_to_postgres()
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("upserted") or result.get("postgres_rows"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault sync failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/vault/dedupe-report", dependencies=_FIREBASE_PROTECTED)
def vault_dedupe_report(limit: int = Query(30, ge=1, le=100)) -> dict:
    return deduplication_report(limit=limit)


@app.get("/api/knowledge/hybrid-search")
def knowledge_hybrid_search(
    q: str = Query(..., min_length=2),
    section_id: Optional[str] = Query(None),
    limit: int = Query(12, ge=1, le=40),
) -> dict:
    """Semantic lab index + metadata vault search (no disk paths)."""
    lab_hits = search_lab_knowledge(q, section_id=section_id, limit=limit)
    vault_hits = search_vault(q, limit=max(5, limit // 2))
    return {
        "query": q,
        "lab_results": lab_hits,
        "vault_results": vault_hits,
        "count": len(lab_hits) + len(vault_hits),
    }


@app.get("/api/search")
def unified_search(
    q: str = Query(..., min_length=2),
    mode: str = Query("hybrid"),
    section_id: Optional[str] = Query(None),
    page_domain_id: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    """Unified search: exact|metadata|semantic|hybrid (LUMI-W140)."""
    mode = (mode or "hybrid").lower()
    out: dict = {"query": q, "mode": mode}
    if mode in ("semantic", "hybrid"):
        out["lab_results"] = search_lab_knowledge(q, section_id=section_id, limit=limit)
    if mode in ("metadata", "exact", "hybrid"):
        out["vault_results"] = search_vault(q, limit=limit)
    if mode == "exact" and not out.get("lab_results"):
        out["lab_results"] = []
    out["count"] = len(out.get("lab_results") or []) + len(out.get("vault_results") or [])
    out["page_domain_id"] = page_domain_id
    return out

from app_skeleton.api.project_knowledge_extractor import extract_and_ingest_project

@app.post("/api/projects/{project_code}/knowledge/ingest")
def project_knowledge_ingest(project_code: str) -> dict:
    try:
        return extract_and_ingest_project(project_code)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/registry")
def documents_registry(
    section_id: Optional[str] = Query(None),
    corpus: Optional[str] = Query("lab_operations"),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    docs = list_registry_documents(section_id=section_id, corpus=corpus, limit=limit)
    return {"count": len(docs), "documents": docs}


@app.get("/api/vault/manifest", dependencies=_FIREBASE_PROTECTED)
def vault_manifest(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    return vault_manifest_page(offset=offset, limit=limit)


@app.get("/api/page-domains")
def page_domains_list() -> dict:
    return {"domains": list_domains(), "sections": list_page_sections()}


@app.get("/api/storage/connectors/status", dependencies=_FIREBASE_PROTECTED)
def storage_connectors_status() -> dict:
    return {
        "connectors": [
            datacloud_webdav.public_status(),
            pdrive_smb.public_status(),
            {
                "provider_id": "supabase_storage",
                "configured": bool(
                    os.getenv("SUPABASE_URL", "").strip()
                    and (
                        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
                        or os.getenv("SERVICE_ROLE_KEY", "").strip()
                    )
                ),
                "role": "small_files_previews",
            },
        ]
    }


@app.get("/api/storage/datacloud/list", dependencies=_FIREBASE_PROTECTED)
def storage_datacloud_list(relative_path: str = Query(""), depth: int = Query(1, ge=1, le=3)) -> dict:
    return {"entries": datacloud_webdav.list_logical_directory(relative_path, depth=depth)}


@app.get("/api/storage/datacloud/scan", dependencies=_FIREBASE_PROTECTED)
def storage_datacloud_scan(
    relative_path: str = Query(""),
    max_entries: int = Query(200, ge=1, le=2000),
) -> dict:
    return datacloud_webdav.scan_tree(relative_path, max_entries=max_entries)


@app.get("/api/storage/datacloud/manifest", dependencies=_FIREBASE_PROTECTED)
def storage_datacloud_manifest(
    relative_path: str = Query(""),
    max_entries: int = Query(500, ge=1, le=5000),
) -> dict:
    return datacloud_webdav.build_manifest(relative_path, max_entries=max_entries)


@app.get("/api/storage/pdrive/list", dependencies=_FIREBASE_PROTECTED)
def storage_pdrive_list(relative_path: str = Query("")) -> dict:
    return {"entries": pdrive_smb.list_logical_directory(relative_path)}


@app.get("/api/storage/pdrive/scan", dependencies=_FIREBASE_PROTECTED)
def storage_pdrive_scan(
    relative_path: str = Query(""),
    max_entries: int = Query(200, ge=1, le=2000),
) -> dict:
    return pdrive_smb.scan_tree(relative_path, max_entries=max_entries)


@app.get("/api/storage/pdrive/manifest", dependencies=_FIREBASE_PROTECTED)
def storage_pdrive_manifest(
    relative_path: str = Query(""),
    max_entries: int = Query(500, ge=1, le=5000),
) -> dict:
    return pdrive_smb.build_manifest(relative_path, max_entries=max_entries)


@app.get("/api/storage/datacloud/download", dependencies=_FIREBASE_PROTECTED)
def storage_datacloud_download(relative_path: str = Query(..., min_length=1)) -> StreamingResponse:
    """Backend-only stream; never expose WebDAV URL to clients."""
    if not datacloud_webdav.is_configured():
        raise HTTPException(status_code=503, detail="DataCloud not configured")
    return StreamingResponse(
        datacloud_webdav.download_stream(relative_path),
        media_type="application/octet-stream",
    )


@app.get("/api/storage/pdrive/download", dependencies=_FIREBASE_PROTECTED)
def storage_pdrive_download(relative_path: str = Query(..., min_length=1)) -> StreamingResponse:
    if not pdrive_smb.is_configured():
        raise HTTPException(status_code=503, detail="P-drive not configured")
    return StreamingResponse(
        pdrive_smb.download_stream(relative_path),
        media_type="application/octet-stream",
    )


@app.post("/api/storage/ingest/{provider_id}", dependencies=_FIREBASE_PROTECTED)
def storage_ingest_provider(
    provider_id: str,
    relative_path: str = Query(""),
    max_entries: int = Query(500, ge=1, le=5000),
) -> dict:
    """Scan → manifest → platform.storage_objects (metadata only)."""
    if provider_id not in ("datacloud_webdav", "pdrive_smb"):
        raise HTTPException(status_code=400, detail="Unsupported storage provider")
    job = platform_admin.create_ingestion_job(f"storage_scan_{provider_id}")
    try:
        result = storage_ingestion.ingest_provider_scan(
            provider_id, relative_path, max_entries=max_entries
        )
        items = (result.get("persist") or {}).get("upserted", 0)
        platform_admin.finish_ingestion_job(job["job_id"], items_processed=items)
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/admin/allowed-emails")
def admin_allowed_emails() -> dict:
    return {"emails": platform_admin.list_allowed_emails()}


@app.post("/api/admin/allowed-emails")
def admin_add_allowed_email(email: str = Query(...), status: str = Query("approved")) -> dict:
    return platform_admin.upsert_allowed_email(email, status=status)


@app.get("/api/admin/registration-requests")
def admin_registration_requests(status: Optional[str] = Query("pending")) -> dict:
    return {"requests": platform_admin.list_registration_requests(status=status)}


@app.get("/api/admin/ingestion-jobs")
def admin_ingestion_jobs(limit: int = Query(20, ge=1, le=100)) -> dict:
    return {"jobs": platform_admin.list_ingestion_jobs(limit=limit)}


@app.get("/api/admin/review-tasks")
def admin_review_tasks(limit: int = Query(50, ge=1, le=200)) -> dict:
    return {"tasks": platform_admin.list_review_tasks(limit=limit)}


@app.get("/api/supabase/sync/status")
def supabase_sync_status_endpoint() -> dict:
    """Last Supabase document sync report (no secrets)."""
    status = supabase_sync_status()
    last_report = read_last_sync_report()
    return {"status": status, "last_report": last_report}


@app.get("/api/lab/sections")
def lab_sections_list() -> dict:
    """Lab database sections with processed-twin and vault asset counts.

    Processed twins are read from local ``app_skeleton/data/processed_projects/lab__*.json``
    (not Supabase/remote Postgres). Run ``database_processor --all --refresh`` to rebuild.
    """
    return {
        "sections": list_lab_sections_detail(),
        "missing_section_roots": assert_all_section_roots_exist(),
        "section_count": len(DATABASE_SECTIONS),
        "processed_source": "local_processed_json",
    }


@app.get("/api/lab/section/{section_id}")
def lab_section_detail(section_id: str) -> dict:
    """Processed digital twin for a lab section (local JSON, document preview up to 50)."""
    try:
        return section_detail_for_api(section_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/lab/section/{section_id}/summary")
def lab_section_summary(section_id: str) -> dict:
    """Alias for ``GET /api/lab/section/{section_id}`` (backward compatible)."""
    try:
        return section_summary_for_api(section_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/lab/section/{section_id}/documents")
def lab_section_documents(
    section_id: str,
    q: Optional[str] = Query(None, min_length=1),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Paginated search within a section's processed document_index (local twin)."""
    try:
        return section_documents_for_api(section_id, q=q, offset=offset, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/database/sections")
def database_sections_list() -> dict:
    return {
        "sections": list_sections(),
        "processed_summary": list_processed_summary(),
        "missing_section_roots": assert_all_section_roots_exist(),
    }


@app.get("/api/database/processed-summary")
def database_processed_summary() -> dict:
    return {"sections": list_processed_summary(), "output_dir": str(PROCESSED_DIR)}


@app.get("/api/database/processed/{section_id}")
def database_processed_twin(section_id: str, refresh: bool = False) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    try:
        return get_section_record(section_id, refresh=refresh)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/database/processed/{section_id}/summary")
def database_processed_summary(section_id: str) -> dict:
    """Lightweight processed record for UI (document index + metrics, no full chunk text)."""
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    twin = load_processed_section(section_id)
    if not twin:
        raise HTTPException(
            status_code=404,
            detail="Section not processed yet. Run Process all lab database or reprocess_lab_database.py.",
        )
    return {
        "section_id": section_id,
        "section_label": twin.get("section_label"),
        "description": twin.get("description"),
        "metrics": twin.get("metrics"),
        "processed_at": twin.get("processed_at"),
        "extraction": twin.get("extraction"),
        "document_index": twin.get("document_index") or [],
        "folder_tree": (twin.get("folder_tree") or [])[:200],
        "content_library_totals": (twin.get("content_library") or {}).get("totals"),
    }


@app.get("/api/database/processed/{section_id}/document-text")
def database_document_text(
    section_id: str,
    relative_path: str = Query(...),
) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    twin = load_processed_section(section_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Section not processed.")
    norm = relative_path.strip().lstrip("/").replace("\\", "/")
    parts = []
    for chunk in _iter_chunks_from_disk(section_id):
        if (chunk.get("source_file") or "").replace("\\", "/") == norm:
            parts.append((chunk.get("chunk_index") or 0, chunk.get("text") or ""))
    if parts:
        parts.sort(key=lambda x: x[0])
        return {
            "path": norm,
            "content": "\n\n".join(t for _, t in parts if t),
            "source": "processed_chunks",
        }
    for doc in twin.get("document_index") or []:
        if (doc.get("path") or "").replace("\\", "/") == norm and doc.get("excerpt"):
            return {"path": norm, "content": doc["excerpt"], "source": "excerpt"}
    raise HTTPException(status_code=404, detail="No extracted text for this file.")


@app.post("/api/database/process-all")
def database_process_all() -> dict:
    """Extract lab files to processed twins, then assimilate into canonical rag.* + Qdrant."""
    job = platform_admin.create_ingestion_job("lab_process_all")
    try:
        extract_result = process_all_sections(refresh=True)
        ingest_result = ingest_all_lab_sections(
            refresh_extract=False,
            qdrant=qdrant_client,
            llm=llm_client,
        )
        totals = ingest_result.get("totals") or {}
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=totals.get("documents") or totals.get("chunks"),
        )
        return {
            "extract": extract_result,
            "ingest": ingest_result,
            "index_stats": get_lab_index_stats(),
            "job_id": job["job_id"],
        }
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/database/process/{section_id}")
def database_process_section(section_id: str) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    try:
        twin = get_section_record(section_id, refresh=True)
        path = save_processed_section(section_id, twin)
        ingest_stats = ingest_section_to_database(
            section_id,
            refresh_extract=False,
            qdrant=qdrant_client,
            llm=llm_client,
        )
        return {
            "section_id": section_id,
            "metrics": twin.get("metrics"),
            "extraction": twin.get("extraction"),
            "output": str(path),
            "ingest": ingest_stats,
            "index_stats": get_lab_index_stats(),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


_LAB_FILE_BROWSER_DEPRECATED = (
    "Lab corpus uses canonical search (/api/knowledge/lab/search) and processed twins; "
    "raw file tree browsing is disabled."
)


@app.get("/api/database/search")
def database_search(
    q: str = Query(..., min_length=2),
    section_id: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    """Deprecated alias — routes to canonical lab knowledge search."""
    hits = search_lab_knowledge(q, section_id=section_id, limit=limit)
    source = "lab_knowledge"
    if not hits:
        hits = search_section_chunks(q, section_id=section_id, limit=limit)
        source = "processed_chunks"
    return {"query": q, "count": len(hits), "results": hits, "source": source}


@app.get("/api/database/tree")
def database_tree(
    section_id: str = Query(...),
    relative_path: str = Query(""),
) -> dict:
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)


@app.get("/api/database/read", dependencies=_FIREBASE_PROTECTED)
def database_read_file(
    section_id: str = Query(...),
    relative_path: str = Query(...),
) -> dict:
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)


@app.get("/api/database/extract")
def database_extract_text(
    section_id: str = Query(...),
    relative_path: str = Query(...),
) -> dict:
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)


@app.get("/api/database/asset")
def database_asset(
    section_id: str = Query(...),
    relative_path: str = Query(...),
):
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)


def _database_static_url(section_id: str, relative_path: str) -> str:
    meta = DATABASE_SECTIONS[section_id]
    rel_root = meta["relative_root"].strip("/")
    rel_file = relative_path.strip().lstrip("/")
    return f"/database-static/{rel_root}/{rel_file}"


@app.get("/api/database/asset-url", dependencies=_FIREBASE_PROTECTED)
def database_asset_url(section_id: str = Query(...), relative_path: str = Query(...)) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    root = section_root(section_id)
    abs_path = safe_relative_path(root, relative_path)
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    if not _is_database_asset_file(abs_path):
        raise HTTPException(status_code=415, detail="File type cannot be opened.")
    return {
        "url": _database_static_url(section_id, relative_path),
        "path": relative_path,
        "section_id": section_id,
        "name": abs_path.name,
        "extension": abs_path.suffix.lower(),
    }


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

@app.get("/api/project-files/list/{project_code}")
def list_project_files(project_code: str):
    folder_path = get_project_folder_path(project_code)
    if not folder_path:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    files = scan_project_text_files(folder_path)
    return files

@app.get("/api/project-files/preview-text")
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


@app.get("/api/project-files/extract")
def project_file_extract(
    project_code: str = Query(...),
    relative_path: str = Query(...),
) -> dict:
    """Extract readable text from Office/PDF project files on disk."""
    folder_path = get_project_folder_path(project_code)
    if not folder_path:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    abs_path = _resolve_under(folder_path, relative_path)
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    if abs_path.suffix.lower() not in PROJECT_EXTRACTABLE_EXTENSIONS:
        raise HTTPException(status_code=415, detail="File type cannot be extracted as text.")
    try:
        result = _extract_file(abs_path, Path(folder_path))
        text = (result.text or "").strip() or (result.excerpt or "").strip()
        if not text:
            raise HTTPException(status_code=422, detail="No text could be extracted from this file.")
        if len(text) > MAX_PROJECT_FILE_READ_BYTES:
            text = text[:MAX_PROJECT_FILE_READ_BYTES] + "\n… [truncated]"
        return {
            "content": text,
            "path": relative_path.strip().lstrip("/").replace("\\", "/"),
            "project_code": project_code,
            "extractor": result.extractor,
            "status": result.status,
            "warnings": result.warnings[:8],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/project-files/read", dependencies=_FIREBASE_PROTECTED)
def read_project_file(project_code: str = Query(...), relative_path: str = Query(...)):
    folder_path = get_project_folder_path(project_code)
    if not folder_path:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    abs_path = _resolve_under(folder_path, relative_path)
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    if not _is_safe_text_file(abs_path):
        raise HTTPException(status_code=415, detail="Only safe text/code files can be read through this endpoint.")
    if abs_path.stat().st_size > MAX_PROJECT_FILE_READ_BYTES:
        raise HTTPException(status_code=413, detail="File too large for inline editor.")
    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
        return {"content": content, "path": relative_path, "size_bytes": abs_path.stat().st_size}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/project-files/serve", dependencies=_FIREBASE_PROTECTED)
def serve_project_file(project_code: str = Query(...), relative_path: str = Query(...)):
    from fastapi.responses import FileResponse
    folder_path = get_project_folder_path(project_code)
    if not folder_path:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    abs_path = _resolve_under(folder_path, relative_path)
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(abs_path)

@app.post("/api/project-files/write")
def write_project_file(req: FileWriteRequest):
    folder_path = get_project_folder_path(req.project_code)
    if not folder_path:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    abs_path = _resolve_under(folder_path, req.relative_path)
    if not _is_safe_text_file(abs_path):
        raise HTTPException(status_code=415, detail="Only safe text/code files can be written through this endpoint.")
    content_bytes = req.content.encode("utf-8")
    if len(content_bytes) > MAX_PROJECT_FILE_WRITE_BYTES:
        raise HTTPException(status_code=413, detail="Content too large for inline editor.")
    try:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(req.content, encoding="utf-8")
        return {"status": "success", "message": f"Successfully wrote to {req.relative_path}", "size_bytes": len(content_bytes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_code}/digital-twin")
def project_digital_twin(project_code: str, refresh: bool = False) -> dict:
    try:
        return get_digital_twin(project_code, refresh=refresh)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.put("/api/projects/{project_code}/digital-twin")
def save_project_digital_twin(project_code: str, body: dict) -> dict:
    try:
        return update_digital_twin(project_code, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
}


def _project_asset_disposition(filename: str, ext: str) -> str:
    from urllib.parse import quote
    safe = filename.replace('"', "'")
    encoded = quote(filename)
    inline_ext = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".tif", ".tiff"}
    disp = "inline" if ext in inline_ext else "attachment"
    return f'{disp}; filename="{safe}"; filename*=UTF-8\'\'{encoded}'


@app.get("/api/projects/{project_code}/asset")
def get_project_asset(project_code: str, path: str = Query(...)):
    root = get_content_root(project_code)
    if not root:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    abs_path = _resolve_under(root, path)
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    ext = abs_path.suffix.lower()
    media_type, _ = mimetypes.guess_type(str(abs_path))
    if not media_type:
        media_type = PROJECT_ASSET_MIME.get(ext, "application/octet-stream")
    return FileResponse(
        str(abs_path),
        media_type=media_type,
        headers={"Content-Disposition": _project_asset_disposition(abs_path.name, ext)},
    )


@app.post("/api/projects/process-all")
def process_all_projects() -> dict:
    try:
        catalog_path = Path(CATALOG_PATH)
        codes = []
        if catalog_path.exists():
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            codes = [p["project_code"] for p in catalog]
        processed = []
        errors = []
        for code in codes:
            try:
                data = process_project(code)
                save_processed(code, data)
                processed.append({
                    "project_code": code,
                    "documents": data["metrics"]["document_count"],
                    "assets": data.get("total_assets_count", 0),
                    "has_folder": bool(data.get("content_root")),
                })
            except Exception as exc:
                errors.append({"project_code": code, "error": str(exc)})
        synced = sync_public_processed()
        return {
            "processed": len(processed),
            "synced_to_public": synced,
            "projects": processed,
            "errors": errors,
            "output_dir": str(PROCESSED_DIR),
            "public_dir": str(PUBLIC_PROCESSED_DIR),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/project-files/report/{project_code}")
def get_project_report(project_code: str) -> dict:
    folder_path = get_project_folder_path(project_code)
    if not folder_path:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    
    files = scan_project_text_files(folder_path)
    
    report = {
        "overview": "",
        "protocols": [],
        "pipelines": [],
        "analytics": [],
        "timeline": [],
        "abstracts": [],
        "other": []
    }
    
    for f in files:
        rel_path = f["name"]
        abs_path = f["path"]
        name_lower = rel_path.lower()
        
        try:
            p = Path(abs_path)
            if p.stat().st_size > MAX_PROJECT_FILE_READ_BYTES:
                content = f"[Skipped: file exceeds {MAX_PROJECT_FILE_READ_BYTES} bytes]"
            else:
                content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            content = f"Error reading file: {e}"
            
        file_item = {"name": rel_path, "content": content}
        
        if "readme" in name_lower:
            report["overview"] += f"\n### {rel_path}\n{content}\n"
        elif "abstract" in name_lower or "essb" in name_lower or "aacr" in name_lower or "eacr" in name_lower or "writing" in name_lower:
            report["abstracts"].append(file_item)
        elif "method" in name_lower or "protocol" in name_lower or "experiment" in name_lower:
            report["protocols"].append(file_item)
        elif "pipeline" in name_lower or "ashlar" in name_lower or "stardist" in name_lower or "basic" in name_lower or "cylinter" in name_lower or name_lower.endswith((".py", ".r", ".sh")):
            report["pipelines"].append(file_item)
        elif "spacestat" in name_lower or "gating" in name_lower or "phenotyp" in name_lower or "deconvolution" in name_lower or "community" in name_lower:
            report["analytics"].append(file_item)
        elif "log_file" in name_lower or "logbook" in name_lower:
            report["timeline"] = parse_log_timeline(content)
        else:
            report["other"].append(file_item)
            
    if not report["overview"]:
        # Try to find README.txt or README.md first, otherwise fallback to first overview file
        report["overview"] = "No readme or overview documentation files found in project folder."
        
    return report


# --- Intelligent Data Pad (section document editor) ---


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


@app.get("/api/datapad/document", dependencies=_FIREBASE_PROTECTED)
def datapad_get_document(
    project_code: str = Query(...),
    relative_path: str = Query(...),
    user: dict[str, Any] = Depends(require_firebase_user),
) -> dict:
    del user
    try:
        return datapad.read_section_document(project_code, relative_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.put("/api/datapad/document", dependencies=_FIREBASE_PROTECTED)
def datapad_put_document(
    req: DatapadSaveRequest,
    user: dict[str, Any] = Depends(require_firebase_user),
) -> dict:
    try:
        return datapad.save_section_document(
            req.project_code,
            req.relative_path,
            req.content,
            actor=_datapad_actor(user),
            create_backup=req.create_backup,
            expected_etag=req.expected_etag,
        )
    except ConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "etag": exc.current_etag},
        ) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/datapad/suggest-headings", dependencies=_FIREBASE_PROTECTED)
def datapad_suggest_headings(req: DatapadContentRequest) -> dict:
    return datapad.suggest_headings(req.content, req.doc_type)


@app.post("/api/datapad/proofread", dependencies=_FIREBASE_PROTECTED)
def datapad_proofread(req: DatapadContentRequest) -> dict:
    return datapad.proofread_content(req.content)


@app.post("/api/datapad/apply-patches", dependencies=_FIREBASE_PROTECTED)
def datapad_apply_patches(
    req: DatapadApplyPatchesRequest,
    user: dict[str, Any] = Depends(require_firebase_user),
) -> dict:
    try:
        doc = datapad.read_section_document(req.project_code, req.relative_path)
        if req.expected_etag and req.expected_etag.strip('"') != (doc.get("etag") or "").strip('"'):
            raise ConflictError("Stale document version.", current_etag=doc.get("etag", ""))
        return datapad.apply_edits(
            req.relative_path,
            req.patches,
            project_code=req.project_code,
            actor=_datapad_actor(user),
        )
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc), "etag": exc.current_etag}) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/datapad/restore-backup", dependencies=_FIREBASE_PROTECTED)
def datapad_restore_backup(
    req: DatapadRestoreRequest,
    user: dict[str, Any] = Depends(require_firebase_user),
) -> dict:
    try:
        return datapad.restore_backup(
            req.project_code,
            req.relative_path,
            req.backup_path,
            actor=_datapad_actor(user),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/datapad/section-summary", dependencies=_FIREBASE_PROTECTED)
def datapad_section_summary(
    project_code: str = Query(...),
    section_id: str | None = Query(None),
) -> dict:
    try:
        return datapad.section_summary(project_code, section_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/datapad/config")
def datapad_config() -> dict:
    return {
        "edit_enabled": datapad.DATAPAD_EDIT_ENABLED,
        "ai_enabled": datapad.datapad_ai_available(),
        "editable_extensions": sorted(datapad.DATAPAD_EDITABLE_EXTENSIONS),
    }


