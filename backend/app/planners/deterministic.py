"""GameForge AI — Deterministic Planner.

Keywords-based rule engine planner. Guaranteed to be fast, offline-capable,
and reproducible for testing, local dev, and fallbacks.
"""
import uuid
from typing import Dict, Any, Optional, List
from app.planners.base import BasePlanner
from app.schemas.execution_graph import ExecutionGraph, ExecutionStep, OperationType, StepStatus


class DeterministicPlanner(BasePlanner):
    """Deterministic keyword-matching execution graph builder."""

    async def create_execution_graph(
        self,
        prompt: str,
        scene_context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionGraph:
        p_lower = prompt.lower()
        steps: List[ExecutionStep] = []
        step_idx = 1

        # Check scene_context for existing objects
        existing_objects = scene_context.get("objects", []) if scene_context else []
        target_obj = None

        for obj in existing_objects:
            obj_name = obj.get("name", "").lower()
            obj_type = obj.get("object_type", "").lower()
            if (obj_name and obj_name in p_lower) or (obj_type and obj_type in p_lower):
                target_obj = obj
                break

        # 1. Base shape or target existing object
        if not target_obj:
            if "sphere" in p_lower or "ball" in p_lower:
                radius = 2.0 if ("large" in p_lower or "big" in p_lower) else (0.5 if "small" in p_lower else 1.0)
                steps.append(ExecutionStep(
                    id=f"step_{step_idx}",
                    type=OperationType.CREATE_SPHERE,
                    status=StepStatus.PENDING,
                    parameters={"radius": radius, "name": "GameForge_Sphere"}
                ))
                step_idx += 1
            elif "camera" in p_lower:
                steps.append(ExecutionStep(
                    id=f"step_{step_idx}",
                    type=OperationType.CREATE_CAMERA,
                    status=StepStatus.PENDING,
                    parameters={"location": [4, -4, 3], "fov": 50.0, "name": "GameForge_Camera"}
                ))
                step_idx += 1
            elif "light" in p_lower:
                l_type = "SUN" if "sun" in p_lower else ("SPOT" if "spot" in p_lower else "POINT")
                steps.append(ExecutionStep(
                    id=f"step_{step_idx}",
                    type=OperationType.CREATE_LIGHT,
                    status=StepStatus.PENDING,
                    parameters={"light_type": l_type, "energy": 1000.0, "location": [5, 5, 10]}
                ))
                step_idx += 1
            elif "cube" in p_lower or "box" in p_lower or len(steps) == 0:
                size = 4.0 if ("large" in p_lower or "big" in p_lower) else (1.0 if "small" in p_lower else 2.0)
                steps.append(ExecutionStep(
                    id=f"step_{step_idx}",
                    type=OperationType.CREATE_CUBE,
                    status=StepStatus.PENDING,
                    parameters={"size": size, "name": "GameForge_Cube"}
                ))
                step_idx += 1

        # 2. Material / Color
        color_hex = "#E8B4B8"
        metallic = 0.4
        roughness = 0.5

        base_rgb = [0.91, 0.71, 0.72]
        if "red" in p_lower:
            color_hex = "#FF3333"
            base_rgb = [1.0, 0.2, 0.2]
        elif "blue" in p_lower:
            color_hex = "#3366FF"
            base_rgb = [0.2, 0.4, 1.0]
        elif "green" in p_lower:
            color_hex = "#33FF66"
            base_rgb = [0.2, 1.0, 0.4]
        elif "gold" in p_lower or "yellow" in p_lower:
            color_hex = "#FFD700"
            base_rgb = [1.0, 0.84, 0.0]
        elif "black" in p_lower:
            color_hex = "#1A1A1A"
            base_rgb = [0.05, 0.05, 0.05]
        elif "white" in p_lower:
            color_hex = "#F0F0F0"
            base_rgb = [0.95, 0.95, 0.95]

        if "metallic" in p_lower or "metal" in p_lower:
            metallic = 0.9
            roughness = 0.2
        elif "shiny" in p_lower or "glass" in p_lower:
            roughness = 0.1

        steps.append(ExecutionStep(
            id=f"step_{step_idx}",
            type=OperationType.SET_MATERIAL,
            status=StepStatus.PENDING,
            parameters={
                "color": color_hex,
                "base_color": base_rgb,
                "metallic": metallic,
                "roughness": roughness,
                "target": target_obj.get("id") if target_obj else None
            }
        ))
        step_idx += 1

        # 3. Transform operations
        if "move" in p_lower or "translate" in p_lower or "right" in p_lower or "up" in p_lower:
            x_pos = 2.0 if ("right" in p_lower or "2 meters" in p_lower) else 0.0
            z_pos = 2.0 if "up" in p_lower else 0.0
            steps.append(ExecutionStep(
                id=f"step_{step_idx}",
                type=OperationType.MOVE_OBJECT,
                status=StepStatus.PENDING,
                parameters={"position": [x_pos, 0.0, z_pos]}
            ))
            step_idx += 1

        if "rotate" in p_lower or "spin" in p_lower:
            steps.append(ExecutionStep(
                id=f"step_{step_idx}",
                type=OperationType.ROTATE_OBJECT,
                status=StepStatus.PENDING,
                parameters={"rotation": [0.0, 0.0, 45.0]}
            ))
            step_idx += 1

        if "scale" in p_lower or "stretch" in p_lower:
            steps.append(ExecutionStep(
                id=f"step_{step_idx}",
                type=OperationType.SCALE_OBJECT,
                status=StepStatus.PENDING,
                parameters={"scale": [1.5, 1.5, 1.5]}
            ))
            step_idx += 1

        if "duplicate" in p_lower or "copy" in p_lower:
            steps.append(ExecutionStep(
                id=f"step_{step_idx}",
                type=OperationType.DUPLICATE_OBJECT,
                status=StepStatus.PENDING,
                parameters={"offset": [2.0, 0.0, 0.0]}
            ))
            step_idx += 1

        # 4. Terminal Export step
        steps.append(ExecutionStep(
            id=f"step_{step_idx}",
            type=OperationType.EXPORT_GLB,
            status=StepStatus.PENDING,
            parameters={}
        ))

        return ExecutionGraph(
            id=f"graph_{uuid.uuid4().hex[:8]}",
            version="1.0",
            steps=steps,
            metadata={"prompt": prompt, "planner": "deterministic"}
        )
