"""GameForge AI — API v1 Endpoints.
All real endpoints for the GameForge backend. Every endpoint performs a real operation.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse

from app.schemas.execution_graph import (
    AssetResponse,
    ExportRequest,
    GenerateRequest,
    GenerationJobResponse,
    JobStatus,
)
from app.services.job_manager import job_manager
from app.services.asset_manager import asset_manager
from app.execution.engine import ExecutionEngine

logger = logging.getLogger("gameforge.api")

router = APIRouter()

# Directory where generated GLB assets are saved
PUBLIC_EXPORTS_DIR = Path(__file__).resolve().parents[4] / "public" / "exports"

execution_engine = ExecutionEngine(exports_dir=PUBLIC_EXPORTS_DIR)


# ---------------------------------------------------------------------------
# Background task: runs the full pipeline for a generation job
# ---------------------------------------------------------------------------
def process_generation_job(job_id: str):
    """Background task: validate graph → execute engine → register asset."""
    job = job_manager.get_job(job_id)
    if not job or not job.execution_graph:
        job_manager.update_job(job_id, status=JobStatus.FAILED, error="Invalid job state: missing graph")
        return

    job_manager.update_job(job_id, status=JobStatus.PROCESSING, progress=10.0, current_step="Validating Graph")
    logger.info("Processing job %s: '%s'", job_id, job.prompt[:80])

    # Execute the full pipeline
    job_manager.update_job(job_id, progress=30.0, current_step="Executing 3D Engine")
    success, message, glb_url = execution_engine.execute(job.execution_graph, job_id)

    if success:
        # Register the generated asset
        asset = asset_manager.register_asset(
            name=f"Generated: {job.prompt[:50]}",
            glb_url=glb_url,
        )
        job_manager.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100.0,
            current_step="Completed",
            asset_url=glb_url,
            asset_id=asset.id,
        )
        logger.info("Job %s completed. Asset: %s at %s", job_id, asset.id, glb_url)
    else:
        job_manager.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=f"Execution Failed: {message}",
        )
        logger.error("Job %s failed: %s", job_id, message[:200])


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@router.get("/health")
async def health_check():
    """Backend health check. Used by frontend connection indicator."""
    from app.blender.runner import blender_engine
    return {
        "status": "ok",
        "service": "gameforge-api",
        "blender_available": blender_engine.blender_path is not None,
    }


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------
@router.post("/generate", response_model=GenerationJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_asset(req: GenerateRequest, background_tasks: BackgroundTasks):
    """Create a real generation job. Builds execution graph via active Planner, validates, and executes through Blender."""
    job = await job_manager.create_job_async(req.prompt, req.execution_graph)
    background_tasks.add_task(process_generation_job, job.id)
    logger.info("Accepted generation job %s for prompt: '%s'", job.id, req.prompt[:80])
    return job


# ---------------------------------------------------------------------------
# Scene & Transforms (PropertiesPanel authoritative backend)
# ---------------------------------------------------------------------------
@router.get("/scenes/active")
async def get_active_scene():
    """Retrieve current active scene with all objects and transforms."""
    from app.db.repositories import SceneRepository
    scene = SceneRepository.get_or_create_default_scene()
    return scene


@router.post("/scenes/objects/transform")
async def update_object_transform(req: dict):
    """Authoritative transform edit from PropertiesPanel.
    Builds single-step MOVE/ROTATE/SCALE graph, executes through 3D engine, updates scene database, and returns updated GLB URL.
    """
    from app.db.repositories import SceneRepository
    from app.schemas.execution_graph import ExecutionGraph, ExecutionStep, OperationType, StepStatus
    import uuid

    scene = SceneRepository.get_or_create_default_scene()
    object_name = req.get("object_name", "GameForge_Cube")
    position = req.get("position")
    rotation = req.get("rotation")
    scale = req.get("scale")

    # Update scene DB state
    updated_scene = SceneRepository.update_object_transform(
        scene_id=scene.id,
        object_name=object_name,
        position=position,
        rotation=rotation,
        scale=scale,
    )

    # Build authoritative execution graph to regenerate GLB asset
    steps = [
        ExecutionStep(
            id="step_1",
            type=OperationType.CREATE_CUBE,
            status=StepStatus.PENDING,
            parameters={"size": 2.0, "name": object_name},
        )
    ]
    step_idx = 2

    if position is not None:
        steps.append(ExecutionStep(
            id=f"step_{step_idx}",
            type=OperationType.MOVE_OBJECT,
            status=StepStatus.PENDING,
            parameters={"position": position},
        ))
        step_idx += 1

    if rotation is not None:
        steps.append(ExecutionStep(
            id=f"step_{step_idx}",
            type=OperationType.ROTATE_OBJECT,
            status=StepStatus.PENDING,
            parameters={"rotation": rotation},
        ))
        step_idx += 1

    if scale is not None:
        steps.append(ExecutionStep(
            id=f"step_{step_idx}",
            type=OperationType.SCALE_OBJECT,
            status=StepStatus.PENDING,
            parameters={"scale": scale},
        ))
        step_idx += 1

    steps.append(ExecutionStep(
        id=f"step_{step_idx}",
        type=OperationType.EXPORT_GLB,
        status=StepStatus.PENDING,
        parameters={},
    ))

    transform_graph = ExecutionGraph(id=f"graph_tr_{uuid.uuid4().hex[:8]}", steps=steps)
    
    # Execute graph synchronously to get updated GLB immediately
    job_id = f"job_tr_{uuid.uuid4().hex[:8]}"
    success, message, glb_url = execution_engine.execute(transform_graph, job_id)

    if success:
        asset_manager.register_asset(name=f"Modified: {object_name}", glb_url=glb_url)
        return {
            "success": True,
            "scene": updated_scene,
            "glb_url": glb_url,
            "message": "Transform updated authoritatively on backend",
        }
    else:
        raise HTTPException(status_code=500, detail=f"Transform execution failed: {message}")


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
@router.get("/jobs/{job_id}", response_model=GenerationJobResponse)
async def get_job_status(job_id: str):
    """Get actual status of a generation job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
@router.get("/assets", response_model=list[AssetResponse])
async def list_assets():
    """List all generated assets."""
    return asset_manager.list_assets()


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: str):
    """Get metadata for a specific asset."""
    asset = asset_manager.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")
    return asset


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
@router.post("/export")
async def export_asset(req: ExportRequest):
    """Export/download a generated asset GLB file."""
    asset = asset_manager.get_asset(req.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{req.asset_id}' not found.")

    # Resolve the GLB file path
    glb_filename = asset.glb_url.lstrip("/exports/")
    glb_path = PUBLIC_EXPORTS_DIR / glb_filename
    if not glb_path.exists():
        raise HTTPException(status_code=404, detail="Asset GLB file not found on disk.")

    return FileResponse(
        path=str(glb_path),
        media_type="model/gltf-binary",
        filename=f"{asset.name.replace(' ', '_')}.glb",
    )
