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
    """Fallback GLB generator using trimesh when Blender is unavailable.
    Renders all active meshes in the scene into a unified GLB artifact.
    """
    try:
        import trimesh
        import numpy as np

        # Map of object_name or index -> mesh dict
        scene_meshes = {}
        active_key = None
        mesh_counter = 0

        for step in graph.steps:
            op = step.type
            params = step.parameters

            if op in (OperationType.CREATE_CUBE, OperationType.CREATE_SPHERE):
                mesh_counter += 1
                name = params.get("name", f"Object_{mesh_counter}")
                loc = params.get("location", [0.0, 0.0, 0.0])

                if op == OperationType.CREATE_SPHERE:
                    radius = params.get("radius", 1.0)
                    m = trimesh.creation.icosphere(radius=radius, subdivisions=3)
                else:
                    size = params.get("size", 2.0)
                    m = trimesh.creation.box(extents=(size, size, size))

                m.apply_translation(loc)
                active_key = name
                scene_meshes[active_key] = {
                    "mesh": m,
                    "color": [232, 180, 184, 255],
                    "visible": True,
                }

            elif op == OperationType.DUPLICATE_OBJECT:
                if active_key and active_key in scene_meshes:
                    orig = scene_meshes[active_key]
                    dup_m = orig["mesh"].copy()
                    offset = params.get("offset", [1.0, 0.0, 0.0])
                    dup_m.apply_translation(offset)
                    mesh_counter += 1
                    dup_name = params.get("new_name", f"{active_key}_copy_{mesh_counter}")
                    scene_meshes[dup_name] = {
                        "mesh": dup_m,
                        "color": list(orig["color"]),
                        "visible": True,
                    }
                    active_key = dup_name

            elif op == OperationType.MOVE_OBJECT:
                if active_key and active_key in scene_meshes:
                    pos = params.get("position", [0.0, 0.0, 0.0])
                    # Reset centroid to position
                    scene_meshes[active_key]["mesh"].apply_translation(pos)

            elif op == OperationType.ROTATE_OBJECT:
                if active_key and active_key in scene_meshes:
                    rot_deg = params.get("rotation", [0.0, 0.0, 0.0])
                    rot_rad = [math.radians(d) for d in rot_deg]
                    rot_matrix = trimesh.transformations.euler_matrix(*rot_rad)
                    scene_meshes[active_key]["mesh"].apply_transform(rot_matrix)

            elif op == OperationType.SCALE_OBJECT:
                if active_key and active_key in scene_meshes:
                    scl = params.get("scale", [1.0, 1.0, 1.0])
                    scene_meshes[active_key]["mesh"].apply_scale(scl)

            elif op in (OperationType.SET_MATERIAL, OperationType.CREATE_MATERIAL, OperationType.UPDATE_MATERIAL):
                if active_key and active_key in scene_meshes:
                    base_color = params.get("base_color")
                    if base_color is not None and isinstance(base_color, list) and len(base_color) == 3:
                        scene_meshes[active_key]["color"] = [
                            int(base_color[0] * 255), int(base_color[1] * 255), int(base_color[2] * 255), int(params.get("opacity", 1.0) * 255)
                        ]
                    elif "color" in params:
                        hex_c = params.get("color", "#E8B4B8").lstrip('#')
                        if len(hex_c) == 6:
                            scene_meshes[active_key]["color"] = [
                                int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16), int(params.get("opacity", 1.0) * 255)
                            ]

            elif op == OperationType.ASSIGN_MATERIAL:
                target = params.get("target") or params.get("object_id") or params.get("object_name") or active_key
                if target and target in scene_meshes and "base_color" in params:
                    base_color = params["base_color"]
                    if isinstance(base_color, list) and len(base_color) == 3:
                        scene_meshes[target]["color"] = [
                            int(base_color[0] * 255), int(base_color[1] * 255), int(base_color[2] * 255), int(params.get("opacity", 1.0) * 255)
                        ]

            elif op == OperationType.HIDE_OBJECT:
                target = params.get("target_name") or active_key
                if target and target in scene_meshes:
                    scene_meshes[target]["visible"] = False

            elif op == OperationType.SHOW_OBJECT:
                target = params.get("target_name") or active_key
                if target and target in scene_meshes:
                    scene_meshes[target]["visible"] = True

            elif op == OperationType.DELETE_OBJECT:
                target = params.get("target_name") or active_key
                if target and target in scene_meshes:
                    del scene_meshes[target]
                    active_key = list(scene_meshes.keys())[-1] if scene_meshes else None

        visible_meshes = []
        for key, item in scene_meshes.items():
            if item["visible"]:
                m = item["mesh"].copy()
                m.visual.face_colors = item["color"]
                visible_meshes.append(m)

        if not visible_meshes:
            default_m = trimesh.creation.box(extents=(2.0, 2.0, 2.0))
            default_m.visual.face_colors = [230, 180, 184, 255]
            scene_mesh = default_m
        elif len(visible_meshes) == 1:
            scene_mesh = visible_meshes[0]
        else:
            scene_mesh = trimesh.util.concatenate(visible_meshes)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        scene_mesh.export(output_path, file_type="glb")
        logger.info("Fallback GLB exported with %d objects to %s", len(visible_meshes), output_path)
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
