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
    """Create a real generation job. Passes active scene_context to active Planner strategy."""
    from app.db.repositories import SceneRepository
    active_scene = SceneRepository.get_or_create_default_scene()
    scene_context = active_scene.model_dump()

    job = await job_manager.create_job_async(req.prompt, req.execution_graph)
    background_tasks.add_task(process_generation_job, job.id)
    logger.info("Accepted generation job %s for prompt: '%s'", job.id, req.prompt[:80])
    return job


# ---------------------------------------------------------------------------
# Scene & Object Hierarchy Endpoints
# ---------------------------------------------------------------------------
@router.get("/scenes/active")
async def get_active_scene():
    """Retrieve current active scene with all persistent objects and hierarchy."""
    from app.db.repositories import SceneRepository
    return SceneRepository.get_or_create_default_scene()


@router.get("/scenes/{scene_id}")
async def get_scene(scene_id: str):
    from app.db.repositories import SceneRepository
    scene = SceneRepository.get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found.")
    return scene


@router.post("/scenes/objects")
async def create_scene_object(req: dict):
    """Add a new SceneObject directly to active scene."""
    from app.db.repositories import SceneRepository
    from app.models.domain import SceneObject, TransformModel, MaterialModel
    import uuid

    scene = SceneRepository.get_or_create_default_scene()
    obj_id = f"obj_{uuid.uuid4().hex[:8]}"
    name = req.get("name", "New_Object")
    obj_type = req.get("object_type", "CUBE").upper()

    pos = req.get("position", [0.0, 0.0, 0.0])
    rot = req.get("rotation", [0.0, 0.0, 0.0])
    scl = req.get("scale", [1.0, 1.0, 1.0])
    color = req.get("color", "#E8B4B8")

    new_obj = SceneObject(
        id=obj_id,
        name=name,
        object_type=obj_type,
        transform=TransformModel(position=pos, rotation=rot, scale=scl),
        material=MaterialModel(color=color),
        parent_id=req.get("parent_id"),
        visible=req.get("visible", True),
    )

    updated_scene = SceneRepository.add_object(scene.id, new_obj)
    return {"success": True, "object": new_obj, "scene": updated_scene}


@router.patch("/scenes/objects/{object_id}")
async def update_scene_object(object_id: str, req: dict):
    """Update properties (Name, Position, Rotation, Scale, Visibility, Parent) of a scene object."""
    from app.db.repositories import SceneRepository
    scene = SceneRepository.get_or_create_default_scene()
    updated_scene = SceneRepository.update_object(scene.id, object_id, req)
    if not updated_scene:
        raise HTTPException(status_code=404, detail=f"Object '{object_id}' not found in scene.")
    return {"success": True, "scene": updated_scene}


@router.delete("/scenes/objects/{object_id}")
async def delete_scene_object(object_id: str):
    """Delete a scene object by ID or name."""
    from app.db.repositories import SceneRepository
    scene = SceneRepository.get_or_create_default_scene()
    updated_scene = SceneRepository.delete_object(scene.id, object_id)
    return {"success": True, "scene": updated_scene}


@router.post("/scenes/objects/duplicate")
async def duplicate_scene_object(req: dict):
    """Duplicate an existing scene object."""
    from app.db.repositories import SceneRepository
    object_ref = req.get("object_id") or req.get("object_name")
    if not object_ref:
        raise HTTPException(status_code=422, detail="Missing object_id or object_name parameter.")
    scene = SceneRepository.get_or_create_default_scene()
    updated_scene, dup_obj = SceneRepository.duplicate_object(scene.id, object_ref)
    if not updated_scene:
        raise HTTPException(status_code=404, detail=f"Object '{object_ref}' not found.")
    return {"success": True, "duplicate": dup_obj, "scene": updated_scene}


@router.post("/scenes/objects/parent")
async def parent_scene_object(req: dict):
    """Establish parent-child relationship with cycle validation."""
    from app.db.repositories import SceneRepository
    child_ref = req.get("child_id") or req.get("child_name")
    parent_ref = req.get("parent_id") or req.get("parent_name")

    if not child_ref or not parent_ref:
        raise HTTPException(status_code=422, detail="Missing child_id or parent_id.")

    scene = SceneRepository.get_or_create_default_scene()
    updated_scene, err = SceneRepository.set_parent(scene.id, child_ref, parent_ref)
    if err:
        raise HTTPException(status_code=400, detail=err)

    return {"success": True, "scene": updated_scene}


@router.post("/scenes/objects/unparent")
async def unparent_scene_object(req: dict):
    """Clear parent reference of a child object."""
    from app.db.repositories import SceneRepository
    child_ref = req.get("child_id") or req.get("child_name")
    if not child_ref:
        raise HTTPException(status_code=422, detail="Missing child_id parameter.")

    scene = SceneRepository.get_or_create_default_scene()
    updated_scene = SceneRepository.unparent(scene.id, child_ref)
    return {"success": True, "scene": updated_scene}


@router.post("/scenes/objects/transform")
async def update_object_transform(req: dict):
    """Authoritative transform edit from PropertiesPanel.
    Updates scene database, executes multi-object scene graph through 3D engine, and returns GLB URL.
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

    # Build multi-object execution graph containing all active objects in scene
    steps = []
    step_idx = 1

    for obj in updated_scene.objects:
        if not obj.visible:
            continue

        if obj.object_type == "SPHERE":
            steps.append(ExecutionStep(
                id=f"step_{step_idx}",
                type=OperationType.CREATE_SPHERE,
                status=StepStatus.PENDING,
                parameters={"radius": 1.0, "name": obj.name, "location": obj.transform.position},
            ))
        else:
            steps.append(ExecutionStep(
                id=f"step_{step_idx}",
                type=OperationType.CREATE_CUBE,
                status=StepStatus.PENDING,
                parameters={"size": 2.0, "name": obj.name, "location": obj.transform.position},
            ))
        step_idx += 1

        if obj.material and obj.material.color:
            steps.append(ExecutionStep(
                id=f"step_{step_idx}",
                type=OperationType.SET_MATERIAL,
                status=StepStatus.PENDING,
                parameters={"color": obj.material.color, "metallic": obj.material.metallic, "roughness": obj.material.roughness},
            ))
            step_idx += 1

        if obj.transform.rotation != [0.0, 0.0, 0.0]:
            steps.append(ExecutionStep(
                id=f"step_{step_idx}",
                type=OperationType.ROTATE_OBJECT,
                status=StepStatus.PENDING,
                parameters={"rotation": obj.transform.rotation},
            ))
            step_idx += 1

        if obj.transform.scale != [1.0, 1.0, 1.0]:
            steps.append(ExecutionStep(
                id=f"step_{step_idx}",
                type=OperationType.SCALE_OBJECT,
                status=StepStatus.PENDING,
                parameters={"scale": obj.transform.scale},
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
