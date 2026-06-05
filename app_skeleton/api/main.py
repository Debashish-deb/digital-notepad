from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app_skeleton.api.common import *
from app_skeleton.api.common import _app_lifespan
from app_skeleton.api.routers import health, research, copilot, knowledge, vault, storage, datapad, digitalization

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
app.include_router(digitalization.router)
