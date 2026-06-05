import ast
import os
import re

def get_source_with_decorators(source_lines, node):
    start_line = node.lineno
    if hasattr(node, 'decorator_list') and node.decorator_list:
        start_line = node.decorator_list[0].lineno
    end_line = node.end_lineno
    node_lines = source_lines[start_line - 1 : end_line]
    return "\n".join(node_lines)

def get_route_path(node):
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            if isinstance(dec.func.value, ast.Name) and dec.func.value.id == "app":
                if dec.args:
                    arg = dec.args[0]
                    if isinstance(arg, ast.Constant):
                        return arg.value
                    elif isinstance(arg, ast.Str):
                        return arg.s
    return None

def is_app_setup(node, source_lines):
    # Check if this node is app setup (app = FastAPI, app.add_middleware, app.mount, etc.)
    src = get_source_with_decorators(source_lines, node)
    if src.startswith("app = FastAPI") or src.startswith("app.add_middleware") or "app.mount(" in src:
        return True
    return False

def main():
    with open("app_skeleton/api/main.py", "r") as f:
        source_code = f.read()

    source_lines = source_code.splitlines()
    tree = ast.parse(source_code)

    commons = []
    main_setup = []
    
    routers = {
        "health": [],
        "research": [],
        "copilot": [],
        "knowledge": [],
        "vault": [],
        "storage": [],
        "datapad": [],
    }

    for node in tree.body:
        # Check if it's a route
        is_route = False
        path = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            path = get_route_path(node)
            if path is not None:
                is_route = True

        if is_route:
            src = get_source_with_decorators(source_lines, node)
            # Replace @app. with @router.
            src = re.sub(r'^@app\.', '@router.', src, flags=re.MULTILINE)
            
            # Categorize route
            if path.startswith("/health") or path.startswith("/stats") or path.startswith("/api/processor/status") or path.startswith("/api/platform/connectors") or path.startswith("/api/auth/config") or path.startswith("/api/admin"):
                routers["health"].append(src)
            elif path.startswith("/projects") or path.startswith("/notebook") or path.startswith("/decisions") or path.startswith("/tasks") or path.startswith("/auto_logs") or path.startswith("/team") or path.startswith("/folders") or path.startswith("/datasets") or path.startswith("/pipeline_runs") or path.startswith("/checklists") or path.startswith("/platform/search") or path.startswith("/infrastructure") or path.startswith("/ai-models") or path.startswith("/publications") or path.startswith("/wiki"):
                routers["research"].append(src)
            elif path.startswith("/ask") or path.startswith("/install_guide") or path.startswith("/lumi_job") or path.startswith("/parse_log") or path.startswith("/run_checker") or path.startswith("/clinical") or path.startswith("/features") or path.startswith("/analysis-runs") or path.startswith("/api/billing-instructions"):
                routers["copilot"].append(src)
            elif path.startswith("/api/knowledge") or path.startswith("/api/database") or path.startswith("/api/search") or path.startswith("/api/documents/registry") or path.startswith("/api/lab"):
                routers["knowledge"].append(src)
            elif path.startswith("/api/vault") or path.startswith("/api/digitalize") or path.startswith("/api/supabase") or path.startswith("/ingest-document") or path.startswith("/gap-analysis"):
                routers["vault"].append(src)
            elif path.startswith("/api/storage"):
                routers["storage"].append(src)
            elif path.startswith("/api/datapad") or path.startswith("/api/project-files") or "/digital-twin" in path or "/asset" in path or "/process-all" in path:
                routers["datapad"].append(src)
            else:
                routers["health"].append(src)
        else:
            # Not a route
            if is_app_setup(node, source_lines):
                main_setup.append(get_source_with_decorators(source_lines, node))
            else:
                commons.append(get_source_with_decorators(source_lines, node))

    # Write common.py
    with open("app_skeleton/api/common.py", "w") as f:
        f.write("\n\n".join(commons))
        f.write("\n\n__all__ = [name for name in globals() if not name.startswith('__')]\n")

    # Write routers
    os.makedirs("app_skeleton/api/routers", exist_ok=True)
    with open("app_skeleton/api/routers/__init__.py", "w") as f:
        f.write("")

    router_header = """from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from app_skeleton.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

"""
    for rname, rsrcs in routers.items():
        with open(f"app_skeleton/api/routers/{rname}.py", "w") as f:
            f.write(router_header)
            f.write("\n\n".join(rsrcs))

    # New main.py
    new_main = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app_skeleton.api.common import *
from app_skeleton.api.common import _app_lifespan
from app_skeleton.api.routers import health, research, copilot, knowledge, vault, storage, datapad

app = FastAPI(title="OMEIA Research Copilot API", version="0.4.0-premium", lifespan=_app_lifespan)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

if CSC_MEDIA_DIR.exists():
    app.mount("/csc-media", StaticFiles(directory=str(MEDIA_DIR) if 'MEDIA_DIR' in globals() else str(CSC_MEDIA_DIR)), name="csc")

if PROJECTS_ROOT.exists():
    app.mount("/projects-static", StaticFiles(directory=str(PROJECTS_ROOT)), name="projects-static")

if DATABASE_ROOT.exists():
    app.mount("/database-static", StaticFiles(directory=str(DATABASE_ROOT)), name="database-static")

app.include_router(health.router)
app.include_router(research.router)
app.include_router(copilot.router)
app.include_router(knowledge.router)
app.include_router(vault.router)
app.include_router(storage.router)
app.include_router(datapad.router)
"""
    with open("app_skeleton/api/main.py", "w") as f:
        f.write(new_main)

    print("Refactoring complete.")
    for rname, rsrcs in routers.items():
        print(f"{rname}: {len(rsrcs)} routes")

if __name__ == "__main__":
    main()
