from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app_skeleton.security.environment import validate_environment
from app_skeleton.security.cors import get_cors_origins
from app_skeleton.security.auth import require_platform_user

# Validate security environment immediately
validate_environment()

from app_skeleton.api.common import *
from app_skeleton.api.common import _app_lifespan
from app_skeleton.api.routers import health, research, copilot, knowledge, vault, storage, datapad, digitalization, search, research_knowledge, chat, document_library, image_assets, biomedical_models, agent_categories
from app_skeleton.security import secure_files

app = FastAPI(title="OMEIA Research Copilot API", version="0.4.0-premium", lifespan=_app_lifespan)

_cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)

# Public static mounts (dev previews — spreadsheet/PDF fetches use /database-static/)
if CSC_MEDIA_DIR.exists():
    app.mount("/csc-media", StaticFiles(directory=str(CSC_MEDIA_DIR)), name="csc-media")

if PROJECTS_ROOT.exists():
    app.mount("/projects-static", StaticFiles(directory=str(PROJECTS_ROOT)), name="projects-static")

if DATABASE_ROOT.exists():
    app.mount("/database-static", StaticFiles(directory=str(DATABASE_ROOT)), name="database-static")

# All standard API routes must require authentication
api_dependencies = [Depends(require_platform_user)]

app.include_router(research.router, dependencies=api_dependencies)
app.include_router(copilot.router, dependencies=api_dependencies)
app.include_router(chat.router, dependencies=api_dependencies)
app.include_router(knowledge.router, dependencies=api_dependencies)
app.include_router(vault.router, dependencies=api_dependencies)
app.include_router(storage.router, dependencies=api_dependencies)
app.include_router(datapad.router, dependencies=api_dependencies)
app.include_router(digitalization.router, dependencies=api_dependencies)
app.include_router(search.router, dependencies=api_dependencies)
app.include_router(research_knowledge.router, dependencies=api_dependencies)
app.include_router(document_library.router, dependencies=api_dependencies)
app.include_router(image_assets.router, dependencies=api_dependencies)
app.include_router(biomedical_models.router, dependencies=api_dependencies)
app.include_router(agent_categories.router, dependencies=api_dependencies)

# Secure files router has its own internal dependency checks, 
# but we can enforce it here as well for defense-in-depth, though it's already in the router definition
app.include_router(secure_files.router)
