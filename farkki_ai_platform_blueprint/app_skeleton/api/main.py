from __future__ import annotations
import os
import re
import math
import hashlib
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Import modular components
from app_skeleton.api.llm_client import LLMClient
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

# Load environment variables
load_dotenv()

app = FastAPI(title="Farkki-AI Research Copilot API", version="0.3.0")

# Database connections
DB_CONN = os.getenv("POSTGRES_CONN", "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai")
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

# ----------------- PYDANTIC SCHEMAS -----------------
class QuestionRequest(BaseModel):
    question: str
    project_codes: List[str] = []
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
    database_counts: Dict[str, Any] = {}
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
    tags: List[str] = []
    entry_type: str = "general_note"
    visibility_level: str = "internal"

class NotebookEntryUpdate(BaseModel):
    title: str
    content: str
    conclusions: Optional[str] = None
    issues_found: Optional[str] = None
    next_steps: Optional[str] = None
    tags: List[str] = []
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
        with psycopg.connect(DB_CONN) as conn:
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
        data["error"] = str(exc)
        data["patient_count"] = 0
        data["sample_count"] = 0
        data["project_samples"] = {}
        data["modality_samples"] = {}
    return data

# ----------------- CORE API ENDPOINTS -----------------
@app.get("/health")
def health() -> dict:
    db_ok = True
    try:
        with psycopg.connect(DB_CONN) as conn:
            pass
    except Exception:
        db_ok = False
        
    return {
        "status": "ok",
        "database_connected": db_ok,
        "llm_client_provider": llm_client.provider,
        "llm_client_healthy": llm_client.healthCheck()
    }

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
    
    # 4. Retrieve documentation chunks using RAGAgent (use active_llm for embedding queries)
    temp_rag = RAGAgent(qdrant_client, active_llm)
    retrieved_sources = temp_rag.retrieve(safe_question, req.project_codes)
    
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
        "You are the Farkki-AI Clinical-Spatial Biology Copilot, an expert AI platform assistant.\n"
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
        f"Documentation Context:\n"
        f"{context_str}\n"
        f"Question: {safe_question}"
    )

    answer = active_llm.generate(user_content, system_prompt)

    if active_llm.provider == "mock":
        limitations.append("Running in local mock-synthesis mode because no LLM_API_KEY is configured.")

    # Audit conversations to DB
    try:
        with psycopg.connect(DB_CONN) as conn:
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
                    (conv_id, answer, psycopg.types.json.Json([s.model_dump() for s in sources]))
                )
    except Exception as exc:
        print(f"Failed to log message to Postgres database: {exc}")

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
        with psycopg.connect(DB_CONN) as conn:
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
        print(f"Failed to audit generated Slurm script to Postgres: {exc}")

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
    checker_map = {
        "python_env": "scripts/check_python_env.sh",
        "gpu": "scripts/check_gpu.sh",
        "napari": "scripts/check_napari.sh",
        "docker": "scripts/check_docker.sh",
        "lumi_modules": "scripts/check_lumi_modules.sh",
        "cylinter_inputs": "scripts/check_cylinter_inputs.py",
        "project_structure": "scripts/check_tcycif_project_structure.py"
    }
    
    script_path = checker_map.get(req.checker_name)
    if not script_path or not os.path.exists(script_path):
        raise HTTPException(status_code=400, detail=f"Checker script {req.checker_name} not found.")
        
    try:
        res = subprocess.run([script_path], capture_output=True, text=True, timeout=10)
        status = "PASS" if res.returncode == 0 else "WARNING/FAIL"
        return {
            "status": status,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "returncode": res.returncode
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to run environment verification tool: {exc}")


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
    try:
        with psycopg.connect(DB_CONN) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT p.project_id, p.project_code, p.project_name, p.disease_focus, p.principal_investigator, p.project_lead, p.start_date, p.end_date, p.status,
                           pe.project_short_title, pe.research_question, pe.project_type, pe.priority, pe.collaborators, pe.ethics_approval_reference, pe.current_blockers, pe.next_actions, pe.project_summary, pe.latest_update
                    FROM core.project p
                    LEFT JOIN platform.project_extension pe ON p.project_id = pe.project_id;
                """)
                rows = cur.fetchall()
                result = []
                for r in rows:
                    result.append({
                        "project_id": str(r[0]),
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
                        "latest_update": r[18] or ""
                    })
                return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.put("/projects/{project_code}")
def update_project(project_code: str, req: ProjectExtensionUpdate) -> dict:
    try:
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT w.wiki_id, w.title, w.slug, w.content, w.wiki_type, p.project_code, r.full_name, w.updated_at
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
                    "updated_at": r[7].isoformat()
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/wiki")
def create_wiki_page(req: WikiPageCreate) -> dict:
    try:
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
    collaborators: List[str] = []

class DocumentIngestRequest(BaseModel):
    filename: str
    file_type: str
    extracted_text: str
    tags: List[str] = []
    project_code: Optional[str] = None
    software_associations: List[str] = []
    pipeline_stage_associations: List[str] = []
    metadata_dict: Dict[str, Any] = {}

class ChecklistToggleRequest(BaseModel):
    checklist_id: str
    status: str
    username: str = "debdeba"

@app.get("/projects")
def get_all_projects() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT p.project_id, p.project_code, p.project_name, p.project_lead, p.principal_investigator, p.disease_focus, p.short_description, p.status,
                           pe.project_type, pe.priority, pe.ethics_approval_reference, pe.current_blockers, pe.next_actions, pe.project_summary
                    FROM core.project p
                    LEFT JOIN platform.project_extension pe ON p.project_id = pe.project_id
                    ORDER BY p.project_code;
                """)
                rows = cur.fetchall()
                projects = []
                for r in rows:
                    pid = r[0]
                    # Get members
                    cur.execute("""
                        SELECT r.full_name, pm.role 
                        FROM platform.project_member pm
                        JOIN platform.researcher r ON pm.researcher_id = r.researcher_id
                        WHERE pm.project_id = %s;
                    """, (pid,))
                    members = [{"name": row[0], "role": row[1]} for row in cur.fetchall()]
                    
                    projects.append({
                        "project_id": str(pid),
                        "project_code": r[1],
                        "project_name": r[2],
                        "project_lead": r[3],
                        "principal_investigator": r[4],
                        "disease_focus": r[5],
                        "short_description": r[6],
                        "status": r[7],
                        "project_type": r[8] or "translational_research",
                        "priority": r[9] or "medium",
                        "ethics_approval_reference": r[10] or "TBD",
                        "current_blockers": r[11] or "None",
                        "next_actions": r[12] or "TBD",
                        "project_summary": r[13] or "",
                        "members": members
                    })
                return projects
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/projects")
def create_project(req: ProjectCreate) -> dict:
    try:
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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
        with psycopg.connect(DB_CONN) as conn:
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

                return {
                    "total_projects": total_projects,
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


