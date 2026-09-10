"""GameForge AI — Backend Application Entry Point."""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints import router as api_v1_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gameforge")

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="GameForge AI — Backend Engine",
    description="AI-native 3D creation studio backend. Manages jobs, execution graphs, Blender execution, and asset serving.",
    version="1.0.0",
)

# CORS — allow frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for exported GLB assets
PUBLIC_EXPORTS_DIR = Path(__file__).parent.parent / "public" / "exports"
PUBLIC_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/exports", StaticFiles(directory=str(PUBLIC_EXPORTS_DIR)), name="exports")

# API routes
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "title": "GameForge AI",
        "version": "1.0.0",
        "docs": "/docs",
    }
