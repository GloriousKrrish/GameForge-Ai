"""GameForge AI — Execution Engine.
Receives a validated ExecutionGraph, dispatches each step to its operation handler,
and tracks step-level status throughout the pipeline.
"""
import logging
import os
import uuid
from pathlib import Path
from typing import Tuple

from app.schemas.execution_graph import ExecutionGraph, OperationType, StepStatus
from app.services.validator import ExecutionGraphValidator
from app.blender.runner import blender_engine

logger = logging.getLogger("gameforge.executor")


class ExecutionEngine:
    """Controlled execution layer that processes an ExecutionGraph through the Blender engine."""

    def __init__(self, exports_dir: Path):
        self.exports_dir = exports_dir

    def execute(self, graph: ExecutionGraph, job_id: str) -> Tuple[bool, str, str]:
        """Execute an entire graph.

        Returns:
            (success, message, glb_relative_url)
        """
        # 1. Validate
        valid, err = ExecutionGraphValidator.validate(graph)
        if not valid:
            logger.error("Graph validation failed for job %s: %s", job_id, err)
            return False, f"Graph Validation Error: {err}", ""

        logger.info("Executing graph '%s' for job %s (%d steps)", graph.id, job_id, len(graph.steps))

        # 2. Mark all steps as PENDING (they already default to PENDING)
        for step in graph.steps:
            step.status = StepStatus.PENDING

        # 3. Determine output path
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        glb_filename = f"{job_id}.glb"
        output_path = str(self.exports_dir / glb_filename)

        # 4. Execute through the Blender engine (or fallback)
        #    The BlenderExecutionEngine handles the full step list
        for step in graph.steps:
            step.status = StepStatus.RUNNING

        success, log_msg = blender_engine.execute(graph, output_path)

        if success and os.path.exists(output_path):
            # Mark all steps as completed
            for step in graph.steps:
                step.status = StepStatus.COMPLETED
            glb_url = f"/exports/{glb_filename}"
            logger.info("Graph execution completed for job %s. GLB at %s", job_id, glb_url)
            return True, log_msg, glb_url
        else:
            # Mark all steps as failed
            for step in graph.steps:
                step.status = StepStatus.FAILED
                step.error = log_msg
            logger.error("Graph execution failed for job %s: %s", job_id, log_msg)
            return False, log_msg, ""
