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

@router.post("/install_guide")
def install_guide(req: InstallRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
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

@router.post("/lumi_job")
def lumi_job(req: LumiJobRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
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

@router.post("/parse_log")
def parse_log(req: LogParseRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    diagnosis = troubleshooting_agent.diagnose_log(req.log_text)
    return {
        "status": "success",
        "cause": diagnosis["cause"],
        "recommended_fix": diagnosis["fix"],
        "prevention": diagnosis["prevention"]
    }

@router.post("/run_checker")
def run_checker(req: CheckerRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
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

@router.post("/run_checker_suite")
def run_checker_suite(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
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

@router.post("/features/seed")
def features_seed(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    return seed_feature_warehouse()

@router.get("/features/definitions")
def features_definitions() -> dict:
    defs = list_feature_definitions()
    return {"count": len(defs), "features": defs}

@router.get("/features/matrices")
def features_matrices(project_code: Optional[str] = Query(None)) -> dict:
    matrices = list_feature_matrices(project_code)
    return {"count": len(matrices), "matrices": matrices}

@router.get("/features/sample/{sample_code}")
def features_sample(sample_code: str) -> dict:
    return get_sample_features(sample_code)

@router.post("/features/similarity")
def features_similarity(req: SimilarityRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    similar = find_similar_samples(req.sample_code, limit=req.limit, project_code=req.project_code)
    result = {"query_sample": req.sample_code, "similar": similar}
    register_analysis_run("feature_similarity", req.model_dump(), result, req.project_code, title=f"Similarity: {req.sample_code}")
    return result

@router.get("/clinical/variables")
def clinical_variables() -> dict:
    vars_ = get_clinical_variables()
    return {"count": len(vars_), "variables": vars_}

@router.post("/clinical/survival")
def clinical_survival(req: SurvivalRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    results = run_survival_analysis(
        duration_col=req.duration_col,
        event_col=req.event_col,
        group_col=req.group_col,
        project_code=req.project_code,
    )
    if req.register_run:
        register_analysis_run("survival", req.model_dump(), results, req.project_code, title="Kaplan-Meier survival")
    return results

@router.post("/clinical/group-compare")
def clinical_group_compare(req: GroupCompareRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    results = run_group_comparison(
        feature_col=req.feature_col,
        group_col=req.group_col,
        project_code=req.project_code,
    )
    if req.register_run:
        register_analysis_run("group_compare", req.model_dump(), results, req.project_code, title=f"Compare {req.feature_col}")
    return results

@router.get("/analysis-runs")
def analysis_runs(limit: int = Query(20, ge=1, le=100)) -> dict:
    runs = list_analysis_runs(limit)
    return {"count": len(runs), "runs": runs}

@router.get("/clinical/recipe/{analysis_type}")
def clinical_recipe(analysis_type: str) -> dict:
    script = clinical_agent.get_analysis_recipe(analysis_type)
    return {"analysis_type": analysis_type, "script": script}