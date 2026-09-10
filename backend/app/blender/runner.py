"""GameForge AI — Blender Execution Runner.
Detects Blender CLI on the system and dispatches execution graphs.
Falls back to trimesh-based GLB generation when Blender is not installed.
"""
import json
import logging
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Optional

from app.schemas.execution_graph import ExecutionGraph, OperationType

logger = logging.getLogger("gameforge.blender")


def find_blender_binary() -> Optional[str]:
    """Finds system Blender executable on PATH or common installation directories."""
    on_path = shutil.which("blender") or shutil.which("blender.exe")
    if on_path:
        return on_path

    # Common Windows installation locations
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    blender_dir = Path(program_files) / "Blender Foundation"
    if blender_dir.exists():
        for sub in sorted(blender_dir.iterdir(), reverse=True):
            candidate = sub / "blender.exe"
            if candidate.exists():
                return str(candidate)

    return None


def generate_fallback_glb(graph: ExecutionGraph, output_path: str) -> bool:
    """Fallback GLB generator using trimesh when Blender is unavailable."""
    try:
        import trimesh
        import numpy as np

        shape_type = "cube"
        color = [230, 180, 184, 255]  # Default rose
        scale = [1.0, 1.0, 1.0]
        position = [0.0, 0.0, 0.0]
        rotation_deg = [0.0, 0.0, 0.0]

        # Track created meshes
        meshes = []

        for step in graph.steps:
            if step.type == OperationType.CREATE_SPHERE:
                radius = step.parameters.get("radius", 1.0)
                m = trimesh.creation.icosphere(radius=radius, subdivisions=3)
                m.apply_translation(step.parameters.get("location", [0, 0, 0]))
                meshes.append(m)
            elif step.type == OperationType.CREATE_CUBE:
                size = step.parameters.get("size", 2.0)
                m = trimesh.creation.box(extents=(size, size, size))
                m.apply_translation(step.parameters.get("location", [0, 0, 0]))
                meshes.append(m)
            elif step.type == OperationType.DUPLICATE_OBJECT:
                if meshes:
                    dup = meshes[-1].copy()
                    offset = step.parameters.get("offset", [1, 0, 0])
                    dup.apply_translation(offset)
                    meshes.append(dup)
            elif step.type == OperationType.SET_MATERIAL:
                hex_c = step.parameters.get("color", "#E8B4B8").lstrip('#')
                if len(hex_c) == 6:
                    color = [int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16), 255]
            elif step.type == OperationType.MOVE_OBJECT:
                position = step.parameters.get("position", position)
            elif step.type == OperationType.SCALE_OBJECT:
                scale = step.parameters.get("scale", scale)
            elif step.type == OperationType.ROTATE_OBJECT:
                rotation_deg = step.parameters.get("rotation", rotation_deg)

        if not meshes:
            mesh = trimesh.creation.box(extents=(2.0, 2.0, 2.0))
        elif len(meshes) == 1:
            mesh = meshes[0]
        else:
            mesh = trimesh.util.concatenate(meshes)

        # Apply scale
        mesh.apply_scale(scale)

        # Apply rotation (degrees -> radians)
        rot_rad = [math.radians(d) for d in rotation_deg]
        rot_matrix = trimesh.transformations.euler_matrix(*rot_rad)
        mesh.apply_transform(rot_matrix)

        # Apply translation
        mesh.apply_translation(position)

        mesh.visual.face_colors = color

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        mesh.export(output_path, file_type="glb")
        logger.info("Fallback GLB exported to %s", output_path)
        return True

    except Exception as e:
        logger.error("Fallback GLB generation failed: %s", e)
        return False


class BlenderExecutionEngine:
    """Orchestrates headless Blender execution or fallback GLB exporter."""

    def __init__(self, blender_path: Optional[str] = None):
        self.blender_path = blender_path or find_blender_binary()
        self.bpy_script_path = str(Path(__file__).parent / "bpy_script.py")

        if self.blender_path:
            logger.info("Blender detected at: %s", self.blender_path)
        else:
            logger.warning("Blender not found on system. Will use fallback trimesh exporter.")

    def execute(self, graph: ExecutionGraph, output_glb_path: str) -> Tuple[bool, str]:
        """Execute an execution graph and produce a GLB file.

        Returns:
            (success, log_message)
        """
        payload = {
            "steps": [step.model_dump() for step in graph.steps],
            "output_path": str(Path(output_glb_path).resolve()),
        }
        payload_str = json.dumps(payload)

        if self.blender_path and os.path.exists(self.blender_path):
            return self._execute_blender(payload_str, output_glb_path)
        else:
            return self._execute_fallback(graph, output_glb_path)

    def _execute_blender(self, payload_str: str, output_glb_path: str) -> Tuple[bool, str]:
        cmd = [
            self.blender_path,
            "--background",
            "--python", self.bpy_script_path,
            "--", payload_str,
        ]
        logger.info("Running Blender: %s", " ".join(cmd[:4]))
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and os.path.exists(output_glb_path):
                return True, f"Blender execution successful. Exported to {output_glb_path}"
            else:
                err_msg = res.stderr or res.stdout or "Unknown error"
                logger.error("Blender process failed (code %d): %s", res.returncode, err_msg[:500])
                return False, f"Blender process failed (code {res.returncode}): {err_msg[:500]}"
        except subprocess.TimeoutExpired:
            return False, "Blender process timed out after 120 seconds."
        except Exception as e:
            return False, f"Failed to execute Blender process: {str(e)}"

    def _execute_fallback(self, graph: ExecutionGraph, output_glb_path: str) -> Tuple[bool, str]:
        logger.info("Using fallback GLB exporter (Blender unavailable)")
        success = generate_fallback_glb(graph, output_glb_path)
        if success:
            return True, f"Generated GLB using fallback engine at {output_glb_path}"
        return False, "Failed to generate GLB using fallback engine."


blender_engine = BlenderExecutionEngine()
