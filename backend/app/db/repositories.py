"""GameForge AI — Repository Layer.

Encapsulates data access logic for Scenes, Projects, and Assets away from API endpoints.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.db.database import db
from app.models.domain import Scene, Project, SceneObject, TransformModel, MaterialModel, CameraModel, LightModel


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
