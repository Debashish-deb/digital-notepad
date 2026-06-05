import re
import os

def main():
    with open("app_skeleton/api/main.py", "r") as f:
        content = f.read()

    # Find the start of the first route
    match = re.search(r'^@app\.(get|post|put|delete|patch)\(', content, re.MULTILINE)
    if not match:
        print("No routes found.")
        return

    first_route_start = match.start()
    
    commons = content[:first_route_start]
    routes_text = content[first_route_start:]

    # Split routes by @app.
    # We can split by looking for \n@app. or ^@app.
    blocks = re.split(r'\n(?=@app\.(?:get|post|put|delete|patch)\()', routes_text)

    routers = {
        "health": [],
        "research": [],
        "copilot": [],
        "knowledge": [],
        "vault": [],
        "storage": [],
        "datapad": [],
    }

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        # In case the block has multiple @app. because of multiple decorators,
        # but the split uses lookahead so it keeps the @app.
        # But wait, our split removes the newline before @app. That's fine.
        
        # Check if it starts with @app.
        if not block.startswith("@app."):
            # It might be a helper function defined between routes.
            # We add it to health for now, or just to common.
            # Let's add it to common!
            commons += "\n\n" + block
            continue

        # Find the path string
        m = re.search(r'@app\.(?:get|post|put|delete|patch)\("([^"]+)"', block)
        if m:
            path = m.group(1)
        else:
            m = re.search(r"@app\.(?:get|post|put|delete|patch)\('([^']+)'", block)
            path = m.group(1) if m else ""

        # Replace @app. with @router.
        block = re.sub(r'^@app\.', '@router.', block, flags=re.MULTILINE)

        if path.startswith("/health") or path.startswith("/stats") or path.startswith("/api/processor/status") or path.startswith("/api/platform/connectors") or path.startswith("/api/auth/config") or path.startswith("/api/admin"):
            routers["health"].append(block)
        elif path.startswith("/projects") or path.startswith("/notebook") or path.startswith("/decisions") or path.startswith("/tasks") or path.startswith("/auto_logs") or path.startswith("/team") or path.startswith("/folders") or path.startswith("/datasets") or path.startswith("/pipeline_runs") or path.startswith("/checklists") or path.startswith("/platform/search") or path.startswith("/infrastructure") or path.startswith("/ai-models") or path.startswith("/publications") or path.startswith("/wiki"):
            routers["research"].append(block)
        elif path.startswith("/ask") or path.startswith("/install_guide") or path.startswith("/lumi_job") or path.startswith("/parse_log") or path.startswith("/run_checker") or path.startswith("/clinical") or path.startswith("/features") or path.startswith("/analysis-runs") or path.startswith("/api/billing-instructions"):
            routers["copilot"].append(block)
        elif path.startswith("/api/knowledge") or path.startswith("/api/database") or path.startswith("/api/search") or path.startswith("/api/documents/registry") or path.startswith("/api/lab"):
            routers["knowledge"].append(block)
        elif path.startswith("/api/vault") or path.startswith("/api/digitalize") or path.startswith("/api/supabase") or path.startswith("/ingest-document") or path.startswith("/gap-analysis"):
            routers["vault"].append(block)
        elif path.startswith("/api/storage"):
            routers["storage"].append(block)
        elif path.startswith("/api/datapad") or path.startswith("/api/project-files") or "/digital-twin" in path or "/asset" in path or "/process-all" in path:
            routers["datapad"].append(block)
        else:
            routers["health"].append(block)

    # Write common.py
    with open("app_skeleton/api/common.py", "w") as f:
        f.write(commons)

    # Write routers
    os.makedirs("app_skeleton/api/routers", exist_ok=True)
    with open("app_skeleton/api/routers/__init__.py", "w") as f:
        f.write("")

    router_header = """from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from app_skeleton.api.common import *
from app_skeleton.api.deps import *
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
from app_skeleton.api.deps import *
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
    app.mount("/csc-media", StaticFiles(directory=str(CSC_MEDIA_DIR)), name="csc")

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
