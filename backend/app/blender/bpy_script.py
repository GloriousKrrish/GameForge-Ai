"""
GameForge AI — Blender BPY Execution Worker Script.

Runs inside headless Blender CLI:
    blender --background --python bpy_script.py -- '<JSON_PAYLOAD>'

Handles all registered operations: CREATE_CUBE, CREATE_SPHERE, DELETE_OBJECT,
MOVE_OBJECT, ROTATE_OBJECT, SCALE_OBJECT, SET_MATERIAL, EXPORT_GLB.
"""
import json
import math
import os
import sys


def hex_to_rgb(hex_str: str):
    """Convert hex color string to RGBA tuple (0.0-1.0)."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return (r, g, b, 1.0)
    return (0.8, 0.8, 0.8, 1.0)


def log(msg: str):
    print(f"[GameForge BPY] {msg}")


def execute_graph(payload_json: str):
    data = json.loads(payload_json)
    steps = data.get("steps", [])
    output_path = data.get("output_path", "output.glb")

    try:
        import bpy
    except ImportError:
        log("ERROR: bpy module not available. This script must run inside Blender.")
        sys.exit(1)

    # 1. Reset Blender to a clean scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # Track the most recently created/active object
    active_obj = None

    # 2. Process each step in order
    for i, step in enumerate(steps):
        op_type = step.get("type")
        params = step.get("parameters", {})
        step_id = step.get("id", f"step_{i}")
        log(f"Step {step_id}: {op_type}")

        # ---- CREATE_CUBE ----
        if op_type == "CREATE_CUBE":
            size = params.get("size", 2.0)
            location = tuple(params.get("location", [0, 0, 0]))
            bpy.ops.mesh.primitive_cube_add(size=size, location=location)
            active_obj = bpy.context.active_object
            active_obj.name = params.get("name", "GameForge_Cube")
            log(f"  Created cube '{active_obj.name}' size={size}")

        # ---- CREATE_SPHERE ----
        elif op_type == "CREATE_SPHERE":
            radius = params.get("radius", 1.0)
            location = tuple(params.get("location", [0, 0, 0]))
            bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location)
            active_obj = bpy.context.active_object
            active_obj.name = params.get("name", "GameForge_Sphere")
            log(f"  Created sphere '{active_obj.name}' radius={radius}")

        # ---- DELETE_OBJECT ----
        elif op_type == "DELETE_OBJECT":
            target_name = params.get("target_name")
            if target_name and target_name in bpy.data.objects:
                obj = bpy.data.objects[target_name]
                bpy.data.objects.remove(obj, do_unlink=True)
                log(f"  Deleted object '{target_name}'")
                if active_obj and active_obj.name == target_name:
                    active_obj = None
            elif active_obj:
                name = active_obj.name
                bpy.data.objects.remove(active_obj, do_unlink=True)
                active_obj = None
                log(f"  Deleted active object '{name}'")

        # ---- MOVE_OBJECT ----
        elif op_type == "MOVE_OBJECT":
            if active_obj:
                position = params.get("position", [0, 0, 0])
                active_obj.location = tuple(position)
                log(f"  Moved '{active_obj.name}' to {position}")

        # ---- ROTATE_OBJECT ----
        elif op_type == "ROTATE_OBJECT":
            if active_obj:
                rotation_deg = params.get("rotation", [0, 0, 0])
                active_obj.rotation_euler = tuple(math.radians(d) for d in rotation_deg)
                log(f"  Rotated '{active_obj.name}' by {rotation_deg} degrees")

        # ---- SCALE_OBJECT ----
        elif op_type == "SCALE_OBJECT":
            if active_obj:
                scale = params.get("scale", [1, 1, 1])
                active_obj.scale = tuple(scale)
                log(f"  Scaled '{active_obj.name}' to {scale}")

        # ---- SET_MATERIAL / CREATE_MATERIAL / UPDATE_MATERIAL ----
        elif op_type in ("SET_MATERIAL", "CREATE_MATERIAL", "UPDATE_MATERIAL"):
            mat_name = params.get("name", f"Material_{step_id}")
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            bsdf = nodes.get("Principled BSDF")

            if bsdf:
                # Base Color
                base_color = params.get("base_color")
                if base_color is not None and isinstance(base_color, list) and len(base_color) == 3:
                    bsdf.inputs['Base Color'].default_value = (base_color[0], base_color[1], base_color[2], 1.0)
                elif "color" in params:
                    color_hex = params.get("color", "#E8B4B8")
                    bsdf.inputs['Base Color'].default_value = hex_to_rgb(color_hex)

                # Metallic
                if 'Metallic' in bsdf.inputs and 'metallic' in params:
                    bsdf.inputs['Metallic'].default_value = float(params["metallic"])

                # Roughness
                if 'Roughness' in bsdf.inputs and 'roughness' in params:
                    bsdf.inputs['Roughness'].default_value = float(params["roughness"])

                # Emission
                emission_color = params.get("emission_color")
                if emission_color is not None and 'Emission Color' in bsdf.inputs:
                    bsdf.inputs['Emission Color'].default_value = (emission_color[0], emission_color[1], emission_color[2], 1.0)
                if 'emission_strength' in params and 'Emission Strength' in bsdf.inputs:
                    bsdf.inputs['Emission Strength'].default_value = float(params["emission_strength"])

                # Opacity / Alpha
                if 'opacity' in params and 'Alpha' in bsdf.inputs:
                    alpha_val = float(params["opacity"])
                    bsdf.inputs['Alpha'].default_value = alpha_val

                # Alpha Mode
                alpha_mode = params.get("alpha_mode", "OPAQUE")
                if alpha_mode == "BLEND":
                    mat.blend_method = 'BLEND'
                elif alpha_mode == "MASK":
                    mat.blend_method = 'CLIP'
                else:
                    mat.blend_method = 'OPAQUE'

                # Double Sided
                if "double_sided" in params:
                    mat.use_backface_culling = not bool(params["double_sided"])

            target_ref = params.get("target") or params.get("object_id") or params.get("object_name")
            target_obj = bpy.data.objects.get(target_ref) if target_ref else active_obj
            if target_obj and hasattr(target_obj, "data") and hasattr(target_obj.data, "materials"):
                if not target_obj.data.materials:
                    target_obj.data.materials.append(mat)
                else:
                    target_obj.data.materials[0] = mat
                log(f"  Applied material '{mat.name}' to object '{target_obj.name}'")

        # ---- ASSIGN_MATERIAL ----
        elif op_type == "ASSIGN_MATERIAL":
            mat_ref = params.get("material_id") or params.get("material_name") or params.get("name")
            target_ref = params.get("target") or params.get("object_id") or params.get("object_name")
            mat = bpy.data.materials.get(mat_ref)
            target_obj = bpy.data.objects.get(target_ref) if target_ref else active_obj

            if mat and target_obj and hasattr(target_obj, "data") and hasattr(target_obj.data, "materials"):
                if not target_obj.data.materials:
                    target_obj.data.materials.append(mat)
                else:
                    target_obj.data.materials[0] = mat
                log(f"  Assigned material '{mat.name}' to '{target_obj.name}'")
            else:
                log(f"  ASSIGN_MATERIAL warning: material='{mat_ref}' or target='{target_ref}' not resolved in Blender.")

        # ---- CREATE_CAMERA ----
        elif op_type == "CREATE_CAMERA":
            location = tuple(params.get("location", [4, -4, 3]))
            rotation = tuple(math.radians(d) for d in params.get("rotation", [60, 0, 45]))
            bpy.ops.object.camera_add(location=location, rotation=rotation)
            cam_obj = bpy.context.active_object
            cam_obj.name = params.get("name", "GameForge_Camera")
            if "fov" in params:
                cam_obj.data.lens = params.get("fov")
            active_obj = cam_obj
            log(f"  Created camera '{cam_obj.name}' at {location}")

        # ---- CREATE_LIGHT ----
        elif op_type == "CREATE_LIGHT":
            light_type = params.get("light_type", "SUN").upper()
            location = tuple(params.get("location", [5, 5, 10]))
            bpy.ops.object.light_add(type=light_type, location=location)
            light_obj = bpy.context.active_object
            light_obj.name = params.get("name", f"GameForge_Light_{light_type}")
            if "energy" in params:
                light_obj.data.energy = params.get("energy")
            active_obj = light_obj
            log(f"  Created light '{light_obj.name}' type={light_type} at {location}")

        # ---- DUPLICATE_OBJECT ----
        elif op_type == "DUPLICATE_OBJECT":
            if active_obj:
                bpy.ops.object.duplicate(linked=False)
                dup_obj = bpy.context.active_object
                offset = params.get("offset", [1, 0, 0])
                dup_obj.location.x += offset[0]
                dup_obj.location.y += offset[1]
                dup_obj.location.z += offset[2]
                if "new_name" in params:
                    dup_obj.name = params.get("new_name")
                active_obj = dup_obj
                log(f"  Duplicated active object as '{dup_obj.name}'")

        # ---- PARENT_OBJECT ----
        elif op_type == "PARENT_OBJECT":
            parent_name = params.get("parent")
            if active_obj and parent_name and parent_name in bpy.data.objects:
                parent_obj = bpy.data.objects[parent_name]
                active_obj.parent = parent_obj
                log(f"  Parented '{active_obj.name}' to '{parent_name}'")

        # ---- UNPARENT_OBJECT ----
        elif op_type == "UNPARENT_OBJECT":
            if active_obj and active_obj.parent:
                log(f"  Unparented '{active_obj.name}' from '{active_obj.parent.name}'")
                active_obj.parent = None

        # ---- RENAME_OBJECT ----
        elif op_type == "RENAME_OBJECT":
            new_name = params.get("new_name")
            if active_obj and new_name:
                log(f"  Renamed '{active_obj.name}' to '{new_name}'")
                active_obj.name = new_name

        # ---- HIDE_OBJECT ----
        elif op_type == "HIDE_OBJECT":
            if active_obj:
                active_obj.hide_viewport = True
                active_obj.hide_render = True
                log(f"  Hid object '{active_obj.name}'")

        # ---- SHOW_OBJECT ----
        elif op_type == "SHOW_OBJECT":
            if active_obj:
                active_obj.hide_viewport = False
                active_obj.hide_render = False
                log(f"  Showed object '{active_obj.name}'")

        # ---- EXPORT_GLB ----
        elif op_type == "EXPORT_GLB":
            # Add default lighting and camera for scene completeness
            bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
            bpy.ops.object.camera_add(location=(4, -4, 3), rotation=(1.1, 0, 0.8))

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            log(f"  Exporting scene to GLB: {output_path}")
            bpy.ops.export_scene.gltf(
                filepath=output_path,
                export_format='GLB',
                use_selection=False,
            )
            log(f"  Successfully exported GLB to {output_path}")

        else:
            log(f"  WARNING: Unknown operation type '{op_type}', skipping.")


if __name__ == "__main__":
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        if idx + 1 < len(sys.argv):
            raw_payload = sys.argv[idx + 1]
            execute_graph(raw_payload)
        else:
            log("No payload JSON supplied after '--'.")
            sys.exit(1)
    else:
        log("Expected '--' delimiter in CLI arguments.")
        sys.exit(1)
