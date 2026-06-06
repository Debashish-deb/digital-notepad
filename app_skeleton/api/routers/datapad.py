from app_skeleton.security.permissions import require_role
from app_skeleton.security.auth import require_platform_user
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from app_skeleton.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg
from app_skeleton.api.thumbnail_service import generate_thumbnail

router = APIRouter()

@router.get("/api/project-files/list/{project_code}")
def list_project_files(project_code: str):
    folder_path = get_project_folder_path(project_code)
    if not folder_path:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    files = scan_project_text_files(folder_path)
    return files

@router.get("/api/project-files/preview-text")
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

@router.get("/api/project-files/extract")
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

@router.get("/api/project-files/read", dependencies=_FIREBASE_PROTECTED)
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

@router.get("/api/project-files/serve", dependencies=_FIREBASE_PROTECTED)
def serve_project_file(project_code: str = Query(...), relative_path: str = Query(...)):
    from fastapi.responses import FileResponse
    folder_path = get_project_folder_path(project_code)
    if not folder_path:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    abs_path = _resolve_under(folder_path, relative_path)
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(abs_path)

@router.post("/api/project-files/write")
def write_project_file(req: FileWriteRequest, user: dict = Depends(require_platform_user)):
    require_role(user, ["editor", "admin"])
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

@router.get("/api/projects/{project_code}/digital-twin")
def project_digital_twin(project_code: str, refresh: bool = False) -> dict:
    try:
        return get_digital_twin(project_code, refresh=refresh)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.put("/api/projects/{project_code}/digital-twin")
def save_project_digital_twin(project_code: str, body: dict, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        return update_digital_twin(project_code, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/api/projects/{project_code}/asset")
def get_project_asset(project_code: str, path: str = Query(...), preview: bool = False):
    root = get_content_root(project_code)
    if not root:
        raise HTTPException(status_code=404, detail="Project folder not found on disk.")
    abs_path = _resolve_under(root, path)
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
        
    if preview:
        res = generate_thumbnail(abs_path)
        if res.get("status") in ("created", "cached"):
            preview_path = res.get("preview_path")
            if preview_path and Path(preview_path).is_file():
                return FileResponse(
                    preview_path,
                    media_type="image/jpeg",
                    headers={"Content-Disposition": "inline; filename=\"thumbnail.jpg\""},
                )
                
    ext = abs_path.suffix.lower()
    media_type, _ = mimetypes.guess_type(str(abs_path))
    if not media_type:
        media_type = PROJECT_ASSET_MIME.get(ext, "application/octet-stream")
    return FileResponse(
        str(abs_path),
        media_type=media_type,
        headers={"Content-Disposition": _project_asset_disposition(abs_path.name, ext)},
    )

@router.post("/api/projects/process-all")
def process_all_projects(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
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

@router.get("/api/project-files/report/{project_code}")
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

@router.get("/api/datapad/document", dependencies=_FIREBASE_PROTECTED)
def datapad_get_document(
    project_code: str = Query(...),
    relative_path: str = Query(...),
    user: dict[str, Any] = Depends(require_platform_user),
) -> dict:
    del user
    try:
        return datapad.read_section_document(project_code, relative_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.put("/api/datapad/document", dependencies=_FIREBASE_PROTECTED)
def datapad_put_document(
    req: DatapadSaveRequest,
    user: dict[str, Any] = Depends(require_platform_user),
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

@router.post("/api/datapad/suggest-headings", dependencies=_FIREBASE_PROTECTED)
def datapad_suggest_headings(req: DatapadContentRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    return datapad.suggest_headings(req.content, req.doc_type)

@router.post("/api/datapad/proofread", dependencies=_FIREBASE_PROTECTED)
def datapad_proofread(req: DatapadContentRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    return datapad.proofread_content(req.content)

@router.post("/api/datapad/apply-patches", dependencies=_FIREBASE_PROTECTED)
def datapad_apply_patches(
    req: DatapadApplyPatchesRequest,
    user: dict[str, Any] = Depends(require_platform_user),
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

@router.post("/api/datapad/restore-backup", dependencies=_FIREBASE_PROTECTED)
def datapad_restore_backup(
    req: DatapadRestoreRequest,
    user: dict[str, Any] = Depends(require_platform_user),
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

@router.get("/api/datapad/section-summary", dependencies=_FIREBASE_PROTECTED)
def datapad_section_summary(
    project_code: str = Query(...),
    section_id: str | None = Query(None),
) -> dict:
    try:
        return datapad.section_summary(project_code, section_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/api/datapad/config")
def datapad_config(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    return {
        "edit_enabled": datapad.DATAPAD_EDIT_ENABLED,
        "ai_enabled": datapad.datapad_ai_available(),
        "editable_extensions": sorted(datapad.DATAPAD_EDITABLE_EXTENSIONS),
    }