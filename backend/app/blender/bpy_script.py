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


def log(msg: str) -> None:
    """Print a log message to stdout so the runner can capture it."""
    print(f"[GameForge BPY] {msg}", flush=True)


def hex_to_rgb(hex_str: str):
    """Convert hex color string to RGBA tuple (0.0-1.0)."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return (r, g, b, 1.0)
    return (0.8, 0.8, 0.8, 1.0)


def create_humanoid_armature(armature_name="GameForge_Armature", rig_name="GameForge_Humanoid_Rig"):
    import bpy
    armature_data = bpy.data.armatures.new(armature_name)
    armature_obj = bpy.data.objects.new(rig_name, armature_data)
    bpy.context.scene.collection.objects.link(armature_obj)
    bpy.context.view_layer.objects.active = armature_obj

    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = armature_data.edit_bones

    bone_defs = [
        ("Root", (0.0, 0.0, 0.0), (0.0, 0.0, 0.2), None),
        ("Spine", (0.0, 0.0, 0.2), (0.0, 0.0, 0.8), "Root"),
        ("Chest", (0.0, 0.0, 0.8), (0.0, 0.0, 1.3), "Spine"),
        ("Neck", (0.0, 0.0, 1.3), (0.0, 0.0, 1.5), "Chest"),
        ("Head", (0.0, 0.0, 1.5), (0.0, 0.0, 1.8), "Neck"),
        ("LeftArm", (0.2, 0.0, 1.2), (0.7, 0.0, 1.2), "Chest"),
        ("RightArm", (-0.2, 0.0, 1.2), (-0.7, 0.0, 1.2), "Chest"),
        ("LeftLeg", (0.2, 0.0, 0.8), (0.2, 0.0, 0.0), "Root"),
        ("RightLeg", (-0.2, 0.0, 0.8), (-0.2, 0.0, 0.0), "Root"),
    ]

    created_bones = {}
    for name, head, tail, parent_name in bone_defs:
        b = edit_bones.new(name)
        b.head = head
        b.tail = tail
        if parent_name and parent_name in created_bones:
            b.parent = created_bones[parent_name]
        created_bones[name] = b

    bpy.ops.object.mode_set(mode='OBJECT')
    log(f"  Created Blender Armature '{rig_name}' with {len(bone_defs)} bones.")
    return armature_obj


def skin_mesh_to_armature(mesh_obj, armature_obj, max_influences=4):
    import bpy
    import math

    if not mesh_obj or mesh_obj.type != 'MESH':
        log("  Skinning warning: Target object is not a mesh.")
        return False

    mod_name = "GameForge_Armature_Modifier"
    mod = mesh_obj.modifiers.get(mod_name)
    if not mod:
        mod = mesh_obj.modifiers.new(name=mod_name, type='ARMATURE')
    mod.object = armature_obj

    bone_positions = {}
    for bone in armature_obj.data.bones:
        v = (bone.head_local + bone.tail_local) / 2.0
        bone_positions[bone.name] = (v.x, v.y, v.z)

    vg_map = {}
    for bone_name in bone_positions:
        vg = mesh_obj.vertex_groups.get(bone_name)
        if not vg:
            vg = mesh_obj.vertex_groups.new(name=bone_name)
        vg_map[bone_name] = vg

    mesh_data = mesh_obj.data
    for v in mesh_data.vertices:
        co = v.co
        distances = []
        for b_name, b_pos in bone_positions.items():
            dist = math.sqrt((co.x - b_pos[0])**2 + (co.y - b_pos[1])**2 + (co.z - b_pos[2])**2)
            distances.append((dist, b_name))

        distances.sort(key=lambda x: x[0])
        top_influences = distances[:max_influences]

        weights = []
        inv_sum = 0.0
        for dist, b_name in top_influences:
            w = 1.0 / (dist + 1e-4)
            weights.append((b_name, w))
            inv_sum += w

        for b_name, w in weights:
            norm_w = w / inv_sum
            vg_map[b_name].add([v.index], norm_w, 'REPLACE')

    log(f"  Bound mesh '{mesh_obj.name}' ({len(mesh_data.vertices)} vertices) to armature '{armature_obj.name}'.")
    return True


def apply_procedural_animation_to_armature(armature_obj, params):
    import bpy
    import math
    import mathutils

    if not armature_obj or armature_obj.type != 'ARMATURE':
        log("  Animation warning: Target object is not an Armature.")
        return False

    anim_id = params.get("animation_id", "anim_default")
    preset = params.get("motion_preset") or params.get("animation_type") or "IDLE"
    speed = float(params.get("speed", 1.0))
    amp = float(params.get("amplitude", 1.0))
    duration = float(params.get("duration_seconds", 2.0))
    fps = int(params.get("fps", 30))
    frame_start = int(params.get("frame_start", 1))
    frame_end = int(params.get("frame_end", frame_start + int(duration * fps) - 1))

    total_frames = max(2, frame_end - frame_start + 1)
    bpy.context.scene.frame_start = frame_start
    bpy.context.scene.frame_end = frame_end
    bpy.context.scene.render.fps = fps

    # Action setup
    action_name = f"GameForge_Action_{preset}_{anim_id}"
    action = bpy.data.actions.new(name=action_name)
    if not armature_obj.animation_data:
        armature_obj.animation_data_create()
    armature_obj.animation_data.action = action

    # Map pose bones
    pose_bones = armature_obj.pose.bones
    for pb in pose_bones:
        pb.rotation_mode = 'QUATERNION'

    for f in range(frame_start, frame_end + 1):
        bpy.context.scene.frame_set(f)
        # Normalized frame factor [0..1]
        progress = (f - frame_start) / max(1, total_frames - 1)
        t = progress * 2.0 * math.pi * speed

        # Default bone transforms per frame
        for pb in pose_bones:
            rx, ry, rz = 0.0, 0.0, 0.0
            loc_x, loc_y, loc_z = 0.0, 0.0, 0.0
            name = pb.name

            if preset == "IDLE":
                if name in ("Spine", "Chest"):
                    rx = 0.04 * amp * math.sin(t)
                    rz = 0.02 * amp * math.cos(0.5 * t)
                elif name == "Head":
                    ry = 0.03 * amp * math.sin(0.5 * t)
                elif name == "LeftArm":
                    rz = -0.1 * amp + 0.02 * amp * math.sin(t)
                elif name == "RightArm":
                    rz = 0.1 * amp - 0.02 * amp * math.sin(t)

            elif preset == "WALK":
                if name == "LeftLeg":
                    rx = 0.35 * amp * math.sin(t)
                elif name == "RightLeg":
                    rx = -0.35 * amp * math.sin(t)
                elif name == "LeftArm":
                    rx = -0.25 * amp * math.sin(t)
                elif name == "RightArm":
                    rx = 0.25 * amp * math.sin(t)
                elif name == "Spine":
                    rz = 0.05 * amp * math.sin(t)
                elif name == "Root":
                    loc_z = 0.03 * amp * abs(math.sin(t))

            elif preset == "RUN":
                if name == "LeftLeg":
                    rx = 0.6 * amp * math.sin(t)
                elif name == "RightLeg":
                    rx = -0.6 * amp * math.sin(t)
                elif name == "LeftArm":
                    rx = -0.45 * amp * math.sin(t)
                elif name == "RightArm":
                    rx = 0.45 * amp * math.sin(t)
                elif name in ("Spine", "Chest"):
                    rx = 0.1 * amp
                    rz = 0.08 * amp * math.sin(t)
                elif name == "Root":
                    loc_z = 0.08 * amp * abs(math.sin(t))

            elif preset == "WAVE":
                if name == "RightArm":
                    rx = 1.1 * amp
                    rz = 0.4 * amp
                    ry = 0.35 * amp * math.sin(2.0 * t)
                elif name in ("Chest", "Neck"):
                    rz = 0.05 * amp * math.sin(t)

            elif preset == "JUMP":
                if progress < 0.2:  # Crouch
                    c_phase = math.sin(math.pi * (progress / 0.2))
                    if name in ("LeftLeg", "RightLeg"):
                        rx = 0.3 * amp * c_phase
                    elif name == "Spine":
                        rx = -0.15 * amp * c_phase
                    elif name == "Root":
                        loc_z = -0.15 * amp * c_phase
                elif progress < 0.7:  # Airborne
                    a_phase = math.sin(math.pi * ((progress - 0.2) / 0.5))
                    if name == "Root":
                        loc_z = 0.4 * amp * a_phase
                    elif name in ("LeftArm", "RightArm"):
                        rx = -0.4 * amp * a_phase
                    elif name in ("LeftLeg", "RightLeg"):
                        rx = -0.1 * amp * a_phase
                elif progress < 0.9:  # Landing
                    l_phase = math.sin(math.pi * ((progress - 0.7) / 0.2))
                    if name in ("LeftLeg", "RightLeg"):
                        rx = 0.2 * amp * l_phase
                    elif name == "Root":
                        loc_z = -0.1 * amp * l_phase

            q = mathutils.Euler((rx, ry, rz), 'XYZ').to_quaternion()
            pb.rotation_quaternion = q
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)

            if loc_x != 0.0 or loc_y != 0.0 or loc_z != 0.0:
                pb.location = (loc_x, loc_y, loc_z)
                pb.keyframe_insert(data_path="location", frame=f)

    fcurves_count = len(action.fcurves) if action else 0
    keyframes_count = sum(len(fc.keyframe_points) for fc in action.fcurves) if action else 0
    log(f"  Applied procedural animation '{preset}' to armature '{armature_obj.name}': Action '{action_name}' ({fcurves_count} F-curves, {keyframes_count} keyframes).")
    return fcurves_count > 0


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

        # ---- CREATE_CHARACTER / CLASSIFY_CHARACTER ----
        elif op_type in ("CREATE_CHARACTER", "CLASSIFY_CHARACTER"):
            glb_path = params.get("asset_glb_path") or params.get("glb_path")
            if glb_path and os.path.exists(glb_path):
                log(f"  Importing character mesh GLB into Blender: {glb_path}")
                try:
                    bpy.ops.import_scene.gltf(filepath=glb_path)
                except Exception as exc:
                    log(f"  Warning: failed to import GLB {glb_path}: {exc}")
            else:
                log(f"  Processed {op_type} step for '{params.get('name', 'Character')}'")

        # ---- CREATE_SKELETON / CREATE_RIG / RIG_CHARACTER ----
        elif op_type in ("CREATE_SKELETON", "CREATE_RIG", "RIG_CHARACTER"):
            rig_name = params.get("rig_name", "GameForge_Humanoid_Rig")
            arm_name = params.get("armature_name", "GameForge_Armature")
            armature_obj = create_humanoid_armature(armature_name=arm_name, rig_name=rig_name)
            active_obj = armature_obj

        # ---- SKIN_CHARACTER ----
        elif op_type == "SKIN_CHARACTER":
            armature_ref = params.get("armature_name", "GameForge_Humanoid_Rig")
            armature_obj = bpy.data.objects.get(armature_ref) or next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)

            if not armature_obj:
                armature_obj = create_humanoid_armature()

            # Target mesh objects in scene
            mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
            if not mesh_objs:
                # Create default humanoid mesh representation if none exists
                bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 1.5))
                head_mesh = bpy.context.active_object
                head_mesh.name = "Character_Mesh"
                mesh_objs = [head_mesh]

            max_inf = params.get("max_influences_per_vertex", 4)
            for m in mesh_objs:
                skin_mesh_to_armature(m, armature_obj, max_influences=max_inf)

        # ---- VALIDATE_CHARACTER ----
        elif op_type == "VALIDATE_CHARACTER":
            armature_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
            mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
            log(f"  Character validation check: Armatures={len(armature_objs)}, Meshes={len(mesh_objs)}")

        # ---- CREATE_ANIMATION / APPLY_PROCEDURAL_ANIMATION / VALIDATE_ANIMATION ----
        elif op_type in ("CREATE_ANIMATION", "APPLY_PROCEDURAL_ANIMATION"):
            armature_ref = params.get("armature_name") or params.get("rig_name")
            armature_obj = bpy.data.objects.get(armature_ref) if armature_ref else next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)

            if not armature_obj:
                armature_obj = create_humanoid_armature()

            # Ensure mesh exists & skinned
            mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
            if not mesh_objs:
                bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 1.5))
                head_mesh = bpy.context.active_object
                head_mesh.name = "Character_Mesh"
                mesh_objs = [head_mesh]

            for m in mesh_objs:
                skin_mesh_to_armature(m, armature_obj)

            apply_procedural_animation_to_armature(armature_obj, params)

        elif op_type == "VALIDATE_ANIMATION":
            armature_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
            has_action = any(o.animation_data and o.animation_data.action for o in armature_objs)
            log(f"  Animation validation check: Armatures={len(armature_objs)}, HasAction={has_action}")

        # ---- EXPORT_GLB ----
        elif op_type == "EXPORT_GLB":
            # Add default lighting and camera for scene completeness if missing
            if not any(o.type == 'LIGHT' for o in bpy.data.objects):
                bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
            if not any(o.type == 'CAMERA' for o in bpy.data.objects):
                bpy.ops.object.camera_add(location=(4, -4, 3), rotation=(1.1, 0, 0.8))

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            log(f"  Exporting scene to GLB with skins and armatures: {output_path}")

            export_kwargs = {
                "filepath": output_path,
                "export_format": 'GLB',
                "use_selection": False,
                "export_materials": 'EXPORT',
            }
            # Enable skin and armature export if supported in BPY version
            try:
                bpy.ops.export_scene.gltf(
                    filepath=output_path,
                    export_format='GLB',
                    use_selection=False,
                    export_skins=True,
                    export_all_armatures=True,
                    export_materials='EXPORT',
                )
            except Exception as exc:
                log(f"  gltf export fallback: {exc}")
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
