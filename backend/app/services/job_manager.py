"""GameForge AI — Job Manager & Deterministic Prompt Interpreter.
Creates and tracks generation jobs. Translates simple prompts into ExecutionGraphs
without AI (deterministic keyword matching for Phase 1).
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.schemas.execution_graph import (
    ExecutionGraph,
    ExecutionStep,
    GenerationJobResponse,
    JobStatus,
    OperationType,
)

logger = logging.getLogger("gameforge.jobs")


def default_graph_for_prompt(prompt: str) -> ExecutionGraph:
    """Deterministic prompt-to-graph interpreter for Phase 1.
    Parses keywords from the prompt and builds a structured ExecutionGraph.
    This will be replaced by a real AI Planner in a later phase.
    """
    graph_id = f"graph_{uuid.uuid4().hex[:8]}"
    prompt_lower = prompt.lower()

    steps: List[ExecutionStep] = []
    step_counter = 0

    # --- Shape detection ---
    def next_id() -> str:
        nonlocal step_counter
        step_counter += 1
        return f"step_{step_counter}"

    if "sphere" in prompt_lower:
        radius = 1.0
        if "large" in prompt_lower or "big" in prompt_lower:
            radius = 2.0
        elif "small" in prompt_lower or "tiny" in prompt_lower:
            radius = 0.5
        steps.append(ExecutionStep(
            id=next_id(), type=OperationType.CREATE_SPHERE,
            parameters={"radius": radius},
        ))
    else:
        # Default to cube
        size = 2.0
        if "large" in prompt_lower or "big" in prompt_lower:
            size = 3.0
        elif "small" in prompt_lower or "tiny" in prompt_lower:
            size = 1.0
        steps.append(ExecutionStep(
            id=next_id(), type=OperationType.CREATE_CUBE,
            parameters={"size": size},
        ))

    # --- Color detection ---
    color_map = {
        "red": "#FF0000", "blue": "#0000FF", "green": "#00FF00",
        "gold": "#FFD700", "yellow": "#FFD700", "black": "#111111",
        "white": "#FFFFFF", "orange": "#FF8C00", "purple": "#8B00FF",
        "pink": "#FF69B4", "silver": "#C0C0C0", "grey": "#808080",
        "gray": "#808080",
    }
    color = "#E8B4B8"  # Default rose
    for keyword, hex_val in color_map.items():
        if keyword in prompt_lower:
            color = hex_val
            break

    metallic = 0.8 if ("metallic" in prompt_lower or "metal" in prompt_lower or "chrome" in prompt_lower) else 0.4
    roughness = 0.2 if ("shiny" in prompt_lower or "smooth" in prompt_lower or "glossy" in prompt_lower) else 0.5

    steps.append(ExecutionStep(
        id=next_id(), type=OperationType.SET_MATERIAL,
        parameters={"color": color, "metallic": metallic, "roughness": roughness},
    ))

    # --- Transform detection ---
    if "move" in prompt_lower or "position" in prompt_lower:
        steps.append(ExecutionStep(
            id=next_id(), type=OperationType.MOVE_OBJECT,
            parameters={"position": [0.0, 0.0, 1.0]},
        ))

    if "rotate" in prompt_lower or "rotated" in prompt_lower:
        steps.append(ExecutionStep(
            id=next_id(), type=OperationType.ROTATE_OBJECT,
            parameters={"rotation": [0.0, 0.0, 45.0]},
        ))

    if "scale" in prompt_lower or "scaled" in prompt_lower or "resize" in prompt_lower:
        steps.append(ExecutionStep(
            id=next_id(), type=OperationType.SCALE_OBJECT,
            parameters={"scale": [1.5, 1.5, 1.5]},
        ))

    # --- Always end with export ---
    steps.append(ExecutionStep(
        id=next_id(), type=OperationType.EXPORT_GLB,
        parameters={},
    ))

    logger.info("Built graph '%s' with %d steps from prompt: '%s'", graph_id, len(steps), prompt[:80])
    return ExecutionGraph(id=graph_id, steps=steps)


class JobManager:
    """In-memory lifecycle manager for GameForge AI Generation Jobs.
    Can be replaced with database-backed persistence later.
    """

    def __init__(self):
        self._jobs: Dict[str, GenerationJobResponse] = {}

    async def create_job_async(self, prompt: str, graph: Optional[ExecutionGraph] = None) -> GenerationJobResponse:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        if not graph:
            from app.planners.factory import PlannerFactory
            planner = PlannerFactory.get_planner()
            graph = await planner.create_execution_graph(prompt)

        job = GenerationJobResponse(
            id=job_id,
            prompt=prompt,
            status=JobStatus.QUEUED,
            progress=0.0,
            execution_graph=graph,
            created_at=now,
            updated_at=now,
        )
        self._jobs[job_id] = job
        logger.info("Created job '%s' for prompt: '%s'", job_id, prompt[:80])
        return job

    def create_job(self, prompt: str, graph: Optional[ExecutionGraph] = None) -> GenerationJobResponse:
        """Synchronous wrapper for job creation."""
        import asyncio
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        if not graph:
            from app.planners.factory import PlannerFactory
            planner = PlannerFactory.get_planner()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    graph = default_graph_for_prompt(prompt)
                else:
                    graph = loop.run_until_complete(planner.create_execution_graph(prompt))
            except Exception:
                graph = default_graph_for_prompt(prompt)

        job = GenerationJobResponse(
            id=job_id,
            prompt=prompt,
            status=JobStatus.QUEUED,
            progress=0.0,
            execution_graph=graph,
            created_at=now,
            updated_at=now,
        )
        self._jobs[job_id] = job
        logger.info("Created job '%s' for prompt: '%s'", job_id, prompt[:80])
        return job

    def get_job(self, job_id: str) -> Optional[GenerationJobResponse]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[GenerationJobResponse]:
        return list(self._jobs.values())

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[float] = None,
        current_step: Optional[str] = None,
        asset_url: Optional[str] = None,
        asset_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Optional[GenerationJobResponse]:
        job = self._jobs.get(job_id)
        if not job:
            return None

        now = datetime.now(timezone.utc).isoformat()
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if current_step is not None:
            job.current_step = current_step
        if asset_url is not None:
            job.asset_url = asset_url
        if asset_id is not None:
            job.asset_id = asset_id
        if error is not None:
            job.error = error

        job.updated_at = now
        return job


job_manager = JobManager()
