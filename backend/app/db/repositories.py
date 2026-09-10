"""GameForge AI — Repository Layer.

Encapsulates data access logic for Scenes, Projects, and Assets away from API endpoints.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.db.database import db
from app.models.domain import Scene, Project, SceneObject, TransformModel, MaterialModel, CameraModel, LightModel, Material, AlphaMode, Texture, TextureType


class SceneRepository:
    """Repository for managing Scene persistence."""

    @staticmethod
    def get_or_create_default_scene() -> Scene:
        """Retrieves default active scene or creates one if empty."""
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM scenes ORDER BY created_at ASC LIMIT 1").fetchone()
            if row:
                data = json.loads(row["data_json"])
                return Scene.model_validate(data)

            # Create initial default scene
            default_scene_id = "scene_default"
            default_project_id = "proj_default"
            
            init_scene = Scene(
                id=default_scene_id,
                project_id=default_project_id,
                name="Main Scene",
                objects=[
                    SceneObject(
                        id="obj_default_cube",
                        name="GameForge_Cube",
                        object_type="CUBE",
                        transform=TransformModel(position=[0.0, 0.0, 0.0]),
                        material=MaterialModel(color="#E8B4B8", metallic=0.4, roughness=0.5)
                    )
                ],
                cameras=[CameraModel(id="cam_default")],
                lights=[LightModel(id="light_default")]
            )

            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO scenes (id, project_id, name, data_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (init_scene.id, init_scene.project_id, init_scene.name, json.dumps(init_scene.model_dump()), now_str, now_str)
            )

            # Insert default project
            conn.execute(
                "INSERT OR REPLACE INTO projects (id, name, active_scene_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (default_project_id, "Default Project", default_scene_id, now_str, now_str)
            )

            return init_scene

    @staticmethod
    def get_scene(scene_id: str) -> Optional[Scene]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
            if row:
                data = json.loads(row["data_json"])
                return Scene.model_validate(data)
            return None

    @staticmethod
    def save_scene(scene: Scene) -> Scene:
        scene.updated_at = datetime.now(timezone.utc).isoformat()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scenes (id, project_id, name, data_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (scene.id, scene.project_id, scene.name, json.dumps(scene.model_dump()), scene.created_at, scene.updated_at)
            )
        return scene

    @staticmethod
    def add_object(scene_id: str, new_obj: SceneObject) -> Scene:
        scene = SceneRepository.get_scene(scene_id) or SceneRepository.get_or_create_default_scene()
        scene.objects.append(new_obj)
        return SceneRepository.save_scene(scene)

    @staticmethod
    def update_object(scene_id: str, object_ref: str, updates: dict) -> Optional[Scene]:
        scene = SceneRepository.get_scene(scene_id) or SceneRepository.get_or_create_default_scene()
        target = None
        for obj in scene.objects:
            if obj.id == object_ref or obj.name.lower() == object_ref.lower():
                target = obj
                break

        if not target:
            return None

        if "name" in updates and updates["name"]:
            target.name = updates["name"]
        if "position" in updates and updates["position"] is not None:
            target.transform.position = updates["position"]
        if "rotation" in updates and updates["rotation"] is not None:
            target.transform.rotation = updates["rotation"]
        if "scale" in updates and updates["scale"] is not None:
            target.transform.scale = updates["scale"]
        if "visible" in updates and updates["visible"] is not None:
            target.visible = updates["visible"]
        if "parent_id" in updates:
            target.parent_id = updates["parent_id"]
        if "color" in updates and updates["color"]:
            if not target.material:
                target.material = MaterialModel(color=updates["color"])
            else:
                target.material.color = updates["color"]

        target.updated_at = datetime.now(timezone.utc).isoformat()
        return SceneRepository.save_scene(scene)

    @staticmethod
    def delete_object(scene_id: str, object_ref: str) -> Optional[Scene]:
        scene = SceneRepository.get_scene(scene_id) or SceneRepository.get_or_create_default_scene()
        initial_len = len(scene.objects)
        scene.objects = [o for o in scene.objects if o.id != object_ref and o.name.lower() != object_ref.lower()]
        # Clear child parent_ids referencing deleted object
        for o in scene.objects:
            if o.parent_id == object_ref:
                o.parent_id = None
        if len(scene.objects) < initial_len:
            return SceneRepository.save_scene(scene)
        return scene

    @staticmethod
    def duplicate_object(scene_id: str, object_ref: str) -> Tuple[Optional[Scene], Optional[SceneObject]]:
        scene = SceneRepository.get_scene(scene_id) or SceneRepository.get_or_create_default_scene()
        orig = None
        for obj in scene.objects:
            if obj.id == object_ref or obj.name.lower() == object_ref.lower():
                orig = obj
                break

        if not orig:
            return None, None

        dup_id = f"obj_{uuid.uuid4().hex[:8]}"
        dup_name = f"{orig.name}_copy"
        dup_pos = [orig.transform.position[0] + 1.0, orig.transform.position[1], orig.transform.position[2]]

        dup = SceneObject(
            id=dup_id,
            name=dup_name,
            object_type=orig.object_type,
            transform=TransformModel(position=dup_pos, rotation=list(orig.transform.rotation), scale=list(orig.transform.scale)),
            material=MaterialModel(color=orig.material.color, metallic=orig.material.metallic, roughness=orig.material.roughness) if orig.material else None,
            parent_id=orig.parent_id,
            visible=orig.visible,
        )
        scene.objects.append(dup)
        updated_scene = SceneRepository.save_scene(scene)
        return updated_scene, dup

    @staticmethod
    def set_parent(scene_id: str, child_ref: str, parent_ref: str) -> Tuple[Optional[Scene], Optional[str]]:
        scene = SceneRepository.get_scene(scene_id) or SceneRepository.get_or_create_default_scene()
        child = None
        parent = None

        for o in scene.objects:
            if o.id == child_ref or o.name.lower() == child_ref.lower():
                child = o
            if o.id == parent_ref or o.name.lower() == parent_ref.lower():
                parent = o

        if not child:
            return None, f"Child object '{child_ref}' not found in scene."
        if not parent:
            return None, f"Parent object '{parent_ref}' not found in scene."
        if child.id == parent.id:
            return None, f"Self-parenting rejected: Object '{child.name}' cannot parent to itself."

        # Cycle detection
        curr = parent
        while curr and curr.parent_id:
            if curr.parent_id == child.id:
                return None, f"Circular parenting rejected: '{parent.name}' is already a descendant of '{child.name}'."
            curr = next((o for o in scene.objects if o.id == curr.parent_id), None)

        child.parent_id = parent.id
        return SceneRepository.save_scene(scene), None

    @staticmethod
    def unparent(scene_id: str, child_ref: str) -> Optional[Scene]:
        scene = SceneRepository.get_scene(scene_id) or SceneRepository.get_or_create_default_scene()
        for o in scene.objects:
            if o.id == child_ref or o.name.lower() == child_ref.lower():
                o.parent_id = None
                return SceneRepository.save_scene(scene)
        return scene

    @staticmethod
    def update_object_transform(
        scene_id: str,
        object_name: str,
        position: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
    ) -> Optional[Scene]:
        return SceneRepository.update_object(
            scene_id=scene_id,
            object_ref=object_name,
            updates={"position": position, "rotation": rotation, "scale": scale}
        )


class ProjectRepository:
    """Repository for Project lifecycle."""

    @staticmethod
    def get_project(project_id: str) -> Optional[Project]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if row:
                return Project(
                    id=row["id"],
                    name=row["name"],
                    active_scene_id=row["active_scene_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None


class MaterialRepository:
    """Repository for managing Material domain persistence."""

    PRESETS = [
        {"id": "mat_preset_matte_black", "name": "Matte Black", "base_color": [0.05, 0.05, 0.05], "metallic": 0.0, "roughness": 0.9},
        {"id": "mat_preset_brushed_gold", "name": "Brushed Gold", "base_color": [1.0, 0.766, 0.336], "metallic": 0.9, "roughness": 0.3},
        {"id": "mat_preset_chrome", "name": "Chrome", "base_color": [0.95, 0.95, 0.95], "metallic": 1.0, "roughness": 0.05},
        {"id": "mat_preset_plastic", "name": "Plastic", "base_color": [0.2, 0.5, 0.9], "metallic": 0.0, "roughness": 0.4},
        {"id": "mat_preset_rubber", "name": "Rubber", "base_color": [0.1, 0.1, 0.1], "metallic": 0.0, "roughness": 0.85},
        {"id": "mat_preset_glass", "name": "Glass", "base_color": [0.9, 0.95, 1.0], "metallic": 0.0, "roughness": 0.1, "opacity": 0.3, "alpha_mode": AlphaMode.BLEND},
        {"id": "mat_preset_gold", "name": "Gold", "base_color": [1.0, 0.84, 0.0], "metallic": 0.85, "roughness": 0.2},
    ]

    @staticmethod
    def init_default_presets():
        """Ensure default material presets exist in DB."""
        for p in MaterialRepository.PRESETS:
            if not MaterialRepository.get_material(p["id"]):
                mat = Material(
                    id=p["id"],
                    name=p["name"],
                    base_color=p.get("base_color", [0.9, 0.9, 0.9]),
                    metallic=p.get("metallic", 0.0),
                    roughness=p.get("roughness", 0.5),
                    opacity=p.get("opacity", 1.0),
                    alpha_mode=p.get("alpha_mode", AlphaMode.OPAQUE),
                )
                MaterialRepository.save_material(mat)

    @staticmethod
    def save_material(mat: Material) -> Material:
        mat.updated_at = datetime.now(timezone.utc).isoformat()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO materials (id, name, data_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (mat.id, mat.name, json.dumps(mat.model_dump()), mat.created_at, mat.updated_at)
            )
        return mat

    @staticmethod
    def get_material(material_id: str) -> Optional[Material]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
            if row:
                data = json.loads(row["data_json"])
                return Material.model_validate(data)
            return None

    @staticmethod
    def list_materials() -> List[Material]:
        MaterialRepository.init_default_presets()
        with db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM materials ORDER BY created_at ASC").fetchall()
            materials = []
            for row in rows:
                data = json.loads(row["data_json"])
                materials.append(Material.model_validate(data))
            return materials

    @staticmethod
    def create_material(
        name: str,
        base_color: Optional[List[float]] = None,
        metallic: Optional[float] = None,
        roughness: Optional[float] = None,
        emission_color: Optional[List[float]] = None,
        emission_strength: Optional[float] = None,
        opacity: Optional[float] = None,
        alpha_mode: Optional[AlphaMode] = None,
        double_sided: Optional[bool] = None,
    ) -> Material:
        mat_id = f"mat_{uuid.uuid4().hex[:8]}"
        mat = Material(
            id=mat_id,
            name=name,
            base_color=base_color if base_color is not None else [0.91, 0.71, 0.72],
            metallic=metallic if metallic is not None else 0.4,
            roughness=roughness if roughness is not None else 0.5,
            emission_color=emission_color if emission_color is not None else [0.0, 0.0, 0.0],
            emission_strength=emission_strength if emission_strength is not None else 0.0,
            opacity=opacity if opacity is not None else 1.0,
            alpha_mode=alpha_mode if alpha_mode is not None else AlphaMode.OPAQUE,
            double_sided=double_sided if double_sided is not None else False,
        )
        return MaterialRepository.save_material(mat)

    @staticmethod
    def update_material(material_id: str, updates: dict) -> Optional[Material]:
        mat = MaterialRepository.get_material(material_id)
        if not mat:
            return None

        if "name" in updates and updates["name"]:
            mat.name = updates["name"]
        if "base_color" in updates and updates["base_color"] is not None:
            mat.base_color = updates["base_color"]
        if "metallic" in updates and updates["metallic"] is not None:
            mat.metallic = updates["metallic"]
        if "roughness" in updates and updates["roughness"] is not None:
            mat.roughness = updates["roughness"]
        if "emission_color" in updates and updates["emission_color"] is not None:
            mat.emission_color = updates["emission_color"]
        if "emission_strength" in updates and updates["emission_strength"] is not None:
            mat.emission_strength = updates["emission_strength"]
        if "opacity" in updates and updates["opacity"] is not None:
            mat.opacity = updates["opacity"]
        if "alpha_mode" in updates and updates["alpha_mode"] is not None:
            mat.alpha_mode = updates["alpha_mode"]
        if "double_sided" in updates and updates["double_sided"] is not None:
            mat.double_sided = updates["double_sided"]

        updated_mat = MaterialRepository.save_material(mat)

        # Propagate material property changes to all objects referencing this material_id
        scene = SceneRepository.get_or_create_default_scene()
        modified = False
        hex_color = f"#{int(mat.base_color[0]*255):02X}{int(mat.base_color[1]*255):02X}{int(mat.base_color[2]*255):02X}"
        for obj in scene.objects:
            if obj.material_id == material_id:
                if not obj.material:
                    obj.material = MaterialModel(color=hex_color, metallic=mat.metallic, roughness=mat.roughness)
                else:
                    obj.material.color = hex_color
                    obj.material.metallic = mat.metallic
                    obj.material.roughness = mat.roughness
                modified = True

        if modified:
            SceneRepository.save_scene(scene)

        return updated_mat

    @staticmethod
    def delete_material(material_id: str) -> bool:
        with db.get_connection() as conn:
            cur = conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            deleted = cur.rowcount > 0

        if deleted:
            # Clear material_id reference on objects
            scene = SceneRepository.get_or_create_default_scene()
            modified = False
            for obj in scene.objects:
                if obj.material_id == material_id:
                    obj.material_id = None
                    modified = True
            if modified:
                SceneRepository.save_scene(scene)
        return deleted

    @staticmethod
    def assign_material_to_object(scene_id: str, object_ref: str, material_id: str) -> Tuple[Optional[Scene], Optional[str]]:
        mat = MaterialRepository.get_material(material_id)
        if not mat:
            return None, f"Material '{material_id}' not found."

        scene = SceneRepository.get_scene(scene_id) or SceneRepository.get_or_create_default_scene()
        target = None
        for obj in scene.objects:
            if obj.id == object_ref or obj.name.lower() == object_ref.lower():
                target = obj
                break

        if not target:
            return None, f"Object '{object_ref}' not found in scene."

        target.material_id = mat.id
        hex_color = f"#{int(mat.base_color[0]*255):02X}{int(mat.base_color[1]*255):02X}{int(mat.base_color[2]*255):02X}"
        target.material = MaterialModel(color=hex_color, metallic=mat.metallic, roughness=mat.roughness)
        return SceneRepository.save_scene(scene), None
