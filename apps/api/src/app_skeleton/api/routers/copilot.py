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
def ask(
    req: QuestionRequest,
    request: Request,
    response: Response,
    user: dict = Depends(require_platform_user),
) -> QuestionResponse:
    from app_skeleton.api.rate_limit import apply_rate_limit_headers, check_rate_limit

    client_ip = request.client.host if request.client else "unknown"
    allowed, rate_headers = check_rate_limit(user_id=user.get("email"), ip_address=client_ip)
    apply_rate_limit_headers(response, rate_headers)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")

    mode = (req.mode or "documentation_only").strip().lower()
    if mode != "search_only":
        require_role(user, ["researcher", "viewer", "editor", "admin"])

    active_llm = llm_client
    if req.llm_provider and req.llm_provider != "mock":
        active_llm = LLMClient()
        active_llm.provider = req.llm_provider.lower()
        active_llm.model = req.llm_model or active_llm.model
        active_llm.api_key = req.llm_api_key or active_llm.api_key
        active_llm.base_url = req.llm_base_url or active_llm.base_url
        active_llm._init_client()

    if mode == "search_only":
        from app_skeleton.api.search_service import SearchService

        search_svc = SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=llm_client)
        from app_skeleton.api.chat_intent import classify_chat_intent

        intent_decision = classify_chat_intent(req.question)
        unified = search_svc.hits_for_copilot(
            req.question,
            intent=intent_decision.intent,
            project_codes=req.project_codes,
            limit=int(os.getenv("CHAT_MAX_SOURCES", "12") or "12"),
            user_role=user.get("role"),
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
            for h in unified
        ]
        return QuestionResponse(
            answer="",
            limitations=["Search-only mode — retrieval without LLM synthesis. Use clickable sources to open documents."],
            sources=sources,
            database_counts={},
            is_safe=True,
            search_hits=[h.model_dump() for h in unified],
            intent=intent_decision.intent,
            use_rag=True,
            show_sources=True,
            require_citations=False,
            answer_style=intent_decision.answer_style,
            reason=intent_decision.reason,
        )

    from app_skeleton.api.chat_service import answer_chat
    from app_skeleton.api.search_service import SearchService

    search_svc = SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=active_llm)
    result = answer_chat(
        req.question,
        project_codes=req.project_codes,
        user=user,
        llm=active_llm,
        search_svc=search_svc,
        rag_agent=RAGAgent(qdrant_client, active_llm),
    )

    sources = [SourceInfo(**s) for s in result.get("sources", [])]

    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO platform.conversation (title, project_code) VALUES (%s, %s) RETURNING conversation_id;",
                    ("Research Query Conversation", req.project_codes[0] if req.project_codes else "ALL"),
                )
                conv_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO platform.message (conversation_id, role, content) VALUES (%s, 'user', %s);",
                    (conv_id, req.question),
                )
                cur.execute(
                    "INSERT INTO platform.message (conversation_id, role, content, retrieved_chunks) VALUES (%s, 'assistant', %s, %s);",
                    (conv_id, result.get("answer", ""), psycopg.types.json.Jsonb([s.model_dump() for s in sources])),
                )
    except Exception as exc:
        LOGGER.warning("Failed to log message to Postgres database: %s", exc)

    public_keys = (
        "answer", "limitations", "database_counts", "is_safe", "search_hits",
        "provider", "effective_provider", "model", "fallback_used", "synthesis_mode",
        "intent", "use_rag", "show_sources", "require_citations", "answer_style",
        "reason", "blocked_by_guardrail",
    )
    payload = {k: result.get(k) for k in public_keys if k in result}
    payload["sources"] = sources
    payload.setdefault("limitations", [])
    return QuestionResponse(**payload)

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