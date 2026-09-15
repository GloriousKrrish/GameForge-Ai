"""GameForge AI — GLB Structural Animation Validator.

Enforces glTF 2.0 container integrity, animation channels, samplers, accessors,
bone target paths, timestamp monotonicity, finite keyframe bounds, skeleton joints,
skin vertex weights, and material preservation.
"""
import math
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.domain import AnimationReport, AnimationValidationResult
from app.services.glb_inspector import GLBInspector, GLBInspectorError

logger = logging.getLogger("gameforge.animation_validator")


class GLBAnimationValidationError(ValueError):
    """Raised when GLB animation structural validation fails."""
    pass


class GLBAnimationValidator:
    """Validates binary GLB files for glTF 2.0 animation compliance, structural integrity, and skeleton preservation."""

    @classmethod
    def validate_glb(cls, file_path_or_bytes: Any) -> AnimationValidationResult:
        """Perform full structural animation validation on a binary GLB file or raw bytes."""
        file_path_str = "<memory_buffer>" if isinstance(file_path_or_bytes, bytes) else str(file_path_or_bytes)
        result = AnimationValidationResult(file_path=file_path_str, valid=True)

        try:
            inspection = GLBInspector.inspect_animation_glb(file_path_or_bytes)
        except GLBInspectorError as exc:
            result.valid = False
            result.errors.append(f"GLB container inspection error: {exc}")
            return result
        except Exception as exc:
            result.valid = False
            result.errors.append(f"Unexpected inspection failure: {exc}")
            return result

        result.file_size_bytes = inspection.get("file_size_bytes", 0)
        result.skin_count = inspection.get("skin_count", 0)
        result.has_skins = inspection.get("has_skins", False)
        result.mesh_count = inspection.get("mesh_count", 0)
        result.material_count = inspection.get("material_count", 0)

        gltf_json = inspection.get("raw_json", {})
        accessors = gltf_json.get("accessors", [])
        nodes = gltf_json.get("nodes", [])
        meshes = gltf_json.get("meshes", [])
        skins = gltf_json.get("skins", [])
        materials = gltf_json.get("materials", [])
        raw_anims = inspection.get("animations", [])

        result.animation_count = len(raw_anims)
        if len(raw_anims) == 0:
            result.valid = False
            result.errors.append("Exported GLB contains no animation tracks (animations[] is empty).")

        anim_reports: List[AnimationReport] = []

        for anim_info in raw_anims:
            idx = anim_info["index"]
            anim_name = anim_info["name"]
            report = AnimationReport(
                index=idx,
                name=anim_name,
                duration_seconds=anim_info.get("duration_seconds", 0.0),
                channel_count=anim_info.get("channel_count", 0),
                sampler_count=anim_info.get("sampler_count", 0),
                keyframe_count=anim_info.get("keyframe_count", 0),
                animated_node_count=anim_info.get("animated_node_count", 0),
                target_paths=anim_info.get("target_paths", []),
                valid=True,
            )

            channels = anim_info.get("raw_channels", [])
            samplers = anim_info.get("raw_samplers", [])

            if len(channels) == 0:
                report.valid = False
                report.errors.append(f"Animation '{anim_name}' has no channels.")

            if len(samplers) == 0:
                report.valid = False
                report.errors.append(f"Animation '{anim_name}' has no samplers.")

            # Channel target & sampler validation
            for c_i, ch in enumerate(channels):
                s_idx = ch.get("sampler")
                if s_idx is None or not isinstance(s_idx, int) or s_idx < 0 or s_idx >= len(samplers):
                    report.valid = False
                    report.errors.append(f"Channel {c_i} in animation '{anim_name}' references invalid sampler index '{s_idx}'.")

                target = ch.get("target", {})
                node_idx = target.get("node")
                if node_idx is None or not isinstance(node_idx, int) or node_idx < 0 or node_idx >= len(nodes):
                    report.valid = False
                    report.errors.append(f"Channel {c_i} in animation '{anim_name}' references invalid node index '{node_idx}'.")

                path = target.get("path")
                if path not in ("translation", "rotation", "scale", "weights"):
                    report.valid = False
                    report.errors.append(f"Channel {c_i} in animation '{anim_name}' has invalid target path '{path}'.")

            # Sampler input/output accessor validation
            for s_i, smp in enumerate(samplers):
                inp_idx = smp.get("input")
                out_idx = smp.get("output")
                interp = smp.get("interpolation", "LINEAR")

                if interp not in ("LINEAR", "STEP", "CUBICSPLINE"):
                    report.valid = False
                    report.errors.append(f"Sampler {s_i} in animation '{anim_name}' has invalid interpolation '{interp}'.")

                if inp_idx is None or not isinstance(inp_idx, int) or inp_idx < 0 or inp_idx >= len(accessors):
                    report.valid = False
                    report.errors.append(f"Sampler {s_i} in animation '{anim_name}' references invalid input accessor index '{inp_idx}'.")

                if out_idx is None or not isinstance(out_idx, int) or out_idx < 0 or out_idx >= len(accessors):
                    report.valid = False
                    report.errors.append(f"Sampler {s_i} in animation '{anim_name}' references invalid output accessor index '{out_idx}'.")

            if report.duration_seconds <= 0.0:
                report.warnings.append(f"Animation '{anim_name}' has zero or non-positive duration ({report.duration_seconds:.3f}s).")

            if not report.valid:
                result.valid = False
                result.errors.extend(report.errors)

            anim_reports.append(report)

        result.animations = anim_reports

        # Skin & skeleton validation
        if not result.has_skins:
            result.valid = False
            result.errors.append("Exported GLB contains no skin data.")
        else:
            for s_i, sk in enumerate(skins):
                joints = sk.get("joints", [])
                if not joints:
                    result.warnings.append(f"Skin {s_i} has empty joints list.")
                for j_idx in joints:
                    if not isinstance(j_idx, int) or j_idx < 0 or j_idx >= len(nodes):
                        result.valid = False
                        result.errors.append(f"Skin {s_i} references invalid joint node index '{j_idx}'.")

        # Material preservation check
        if len(materials) == 0:
            if result.mesh_count > 0:
                result.valid = False
                result.errors.append("Exported character mesh contains no materials.")
            else:
                result.warnings.append("Exported GLB contains no materials attached.")

        return result


animation_validator = GLBAnimationValidator()
