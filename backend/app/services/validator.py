"""GameForge AI — Execution Graph Validator.
Validates graph structure, operation types, parameter bounds, and step sequencing
before any execution is allowed.
"""
import logging
from typing import Tuple, Optional
from app.schemas.execution_graph import ExecutionGraph, OperationType

logger = logging.getLogger("gameforge.validator")


class GraphValidationError(Exception):
    """Raised when an execution graph fails validation."""
    pass


class ExecutionGraphValidator:
    """Validates Execution Graph structure, parameter bounds, and step sequencing."""

    ALLOWED_OPERATIONS = set(OperationType)

    @classmethod
    def validate(cls, graph: ExecutionGraph) -> Tuple[bool, Optional[str]]:
        """Validate an execution graph. Returns (is_valid, error_message)."""
        if not graph.steps:
            return False, "Execution graph must contain at least one step."

        step_ids = set()
        has_export = False

        for i, step in enumerate(graph.steps):
            # Duplicate ID check
            if step.id in step_ids:
                return False, f"Duplicate step ID '{step.id}' at index {i}."
            step_ids.add(step.id)

            # Operation type check
            if step.type not in cls.ALLOWED_OPERATIONS:
                return False, f"Unsupported operation '{step.type}' at step '{step.id}'."

            # EXPORT_GLB must be the final step
            if step.type == OperationType.EXPORT_GLB:
                has_export = True
                if i != len(graph.steps) - 1:
                    return False, f"EXPORT_GLB must be the final step in the graph (found at step '{step.id}', index {i})."

            # Per-operation parameter validation
            err = cls._validate_step_parameters(step.type, step.parameters, step.id)
            if err:
                return False, err

        if not has_export:
            return False, "Execution graph missing required EXPORT_GLB terminal step."

        logger.info("Graph '%s' validated successfully (%d steps).", graph.id, len(graph.steps))
        return True, None

    @classmethod
    def _validate_step_parameters(cls, op: OperationType, params: dict, step_id: str) -> Optional[str]:
        """Validate parameters for a specific operation type."""
        if op == OperationType.CREATE_CUBE:
            size = params.get("size", 2.0)
            if not isinstance(size, (int, float)) or size <= 0 or size > 100:
                return f"Invalid cube size '{size}' at step '{step_id}'. Must be between 0 and 100."

        elif op == OperationType.CREATE_SPHERE:
            radius = params.get("radius", 1.0)
            if not isinstance(radius, (int, float)) or radius <= 0 or radius > 50:
                return f"Invalid sphere radius '{radius}' at step '{step_id}'. Must be between 0 and 50."

        elif op == OperationType.SET_MATERIAL:
            color = params.get("color")
            if color is not None and not isinstance(color, str):
                return f"Invalid color value at step '{step_id}'. Must be a hex string."
            metallic = params.get("metallic", 0.4)
            if not isinstance(metallic, (int, float)) or metallic < 0 or metallic > 1:
                return f"Invalid metallic value '{metallic}' at step '{step_id}'. Must be between 0 and 1."
            roughness = params.get("roughness", 0.5)
            if not isinstance(roughness, (int, float)) or roughness < 0 or roughness > 1:
                return f"Invalid roughness value '{roughness}' at step '{step_id}'. Must be between 0 and 1."

        elif op == OperationType.MOVE_OBJECT:
            position = params.get("position")
            if position is not None:
                if not isinstance(position, list) or len(position) != 3:
                    return f"Invalid position at step '{step_id}'. Must be a list of 3 numbers [x, y, z]."

        elif op == OperationType.ROTATE_OBJECT:
            rotation = params.get("rotation")
            if rotation is not None:
                if not isinstance(rotation, list) or len(rotation) != 3:
                    return f"Invalid rotation at step '{step_id}'. Must be a list of 3 numbers [x, y, z] in degrees."

        elif op == OperationType.SCALE_OBJECT:
            scale = params.get("scale")
            if scale is not None:
                if not isinstance(scale, list) or len(scale) != 3:
                    return f"Invalid scale at step '{step_id}'. Must be a list of 3 numbers [x, y, z]."

        elif op == OperationType.CREATE_CAMERA:
            fov = params.get("fov", 50.0)
            if not isinstance(fov, (int, float)) or fov <= 1 or fov > 170:
                return f"Invalid camera FOV '{fov}' at step '{step_id}'. Must be between 1 and 170."

        elif op == OperationType.CREATE_LIGHT:
            energy = params.get("energy", 1000.0)
            if not isinstance(energy, (int, float)) or energy < 0 or energy > 100000:
                return f"Invalid light energy '{energy}' at step '{step_id}'. Must be between 0 and 100000."
            light_type = params.get("light_type", "POINT")
            if light_type not in ("POINT", "SUN", "SPOT", "AREA"):
                return f"Invalid light_type '{light_type}' at step '{step_id}'. Must be POINT, SUN, SPOT, or AREA."

        elif op == OperationType.DUPLICATE_OBJECT:
            # Requires target or uses active object
            pass

        elif op == OperationType.PARENT_OBJECT:
            parent = params.get("parent")
            child = params.get("child") or params.get("target")
            if parent is not None and not isinstance(parent, str):
                return f"Invalid parent reference at step '{step_id}'. Must be an object reference string."
            if parent and child and parent == child:
                return f"Self-parenting rejected at step '{step_id}': Object '{parent}' cannot parent to itself."

        elif op == OperationType.UNPARENT_OBJECT:
            pass

        elif op == OperationType.RENAME_OBJECT:
            new_name = params.get("new_name")
            if not new_name or not isinstance(new_name, str) or len(new_name.strip()) == 0:
                return f"Invalid new_name at step '{step_id}'. Must be a non-empty string."

        elif op in (OperationType.HIDE_OBJECT, OperationType.SHOW_OBJECT):
            pass

        elif op in (OperationType.CREATE_MATERIAL, OperationType.UPDATE_MATERIAL):
            name = params.get("name")
            if op == OperationType.CREATE_MATERIAL and (not name or not isinstance(name, str)):
                return f"Invalid material name at step '{step_id}'. Must be a non-empty string."

            base_color = params.get("base_color")
            if base_color is not None:
                if not isinstance(base_color, list) or len(base_color) != 3 or any(not isinstance(c, (int, float)) or c < 0.0 or c > 1.0 for c in base_color):
                    return f"Invalid base_color at step '{step_id}'. Must be an RGB list of 3 numbers between 0.0 and 1.0."

            metallic = params.get("metallic")
            if metallic is not None:
                if not isinstance(metallic, (int, float)) or metallic < 0.0 or metallic > 1.0:
                    return f"Invalid metallic value '{metallic}' at step '{step_id}'. Must be between 0.0 and 1.0."

            roughness = params.get("roughness")
            if roughness is not None:
                if not isinstance(roughness, (int, float)) or roughness < 0.0 or roughness > 1.0:
                    return f"Invalid roughness value '{roughness}' at step '{step_id}'. Must be between 0.0 and 1.0."

            emission_color = params.get("emission_color")
            if emission_color is not None:
                if not isinstance(emission_color, list) or len(emission_color) != 3 or any(not isinstance(c, (int, float)) or c < 0.0 or c > 1.0 for c in emission_color):
                    return f"Invalid emission_color at step '{step_id}'. Must be an RGB list of 3 numbers between 0.0 and 1.0."

            emission_strength = params.get("emission_strength")
            if emission_strength is not None:
                if not isinstance(emission_strength, (int, float)) or emission_strength < 0.0 or emission_strength > 1000.0:
                    return f"Invalid emission_strength '{emission_strength}' at step '{step_id}'. Must be between 0.0 and 1000.0."

            opacity = params.get("opacity")
            if opacity is not None:
                if not isinstance(opacity, (int, float)) or opacity < 0.0 or opacity > 1.0:
                    return f"Invalid opacity value '{opacity}' at step '{step_id}'. Must be between 0.0 and 1.0."

            alpha_mode = params.get("alpha_mode")
            if alpha_mode is not None and alpha_mode not in ("OPAQUE", "MASK", "BLEND"):
                return f"Invalid alpha_mode '{alpha_mode}' at step '{step_id}'. Must be OPAQUE, MASK, or BLEND."

        elif op == OperationType.ASSIGN_MATERIAL:
            mat_ref = params.get("material_id") or params.get("material_name") or params.get("material")
            if not mat_ref or not isinstance(mat_ref, str):
                return f"Invalid material reference at step '{step_id}'. Must specify material_id or material_name."

        elif op == OperationType.DELETE_OBJECT:
            # target_name is optional; if omitted, deletes the active object
            pass

        elif op == OperationType.EXPORT_GLB:
            # No required parameters
            pass

        return None
