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
    def save_scene(scene: Scene) -> Scene:
        scene.updated_at = datetime.now(timezone.utc).isoformat()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scenes (id, project_id, name, data_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (scene.id, scene.project_id, scene.name, json.dumps(scene.model_dump()), scene.created_at, scene.updated_at)
            )
        return scene

    @staticmethod
    def update_object_transform(
        scene_id: str,
        object_name: str,
        position: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
    ) -> Optional[Scene]:
        """Updates transform parameters for a specified object in the scene."""
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
            if not row:
                return None

            scene_dict = json.loads(row["data_json"])
            scene = Scene.model_validate(scene_dict)

            target_obj = None
            for obj in scene.objects:
                if obj.name.lower() == object_name.lower() or obj.id == object_name:
                    target_obj = obj
                    break

            if not target_obj and scene.objects:
                target_obj = scene.objects[0]  # Active fallback object

            if target_obj:
                if position is not None:
                    target_obj.transform.position = position
                if rotation is not None:
                    target_obj.transform.rotation = rotation
                if scale is not None:
                    target_obj.transform.scale = scale

            return SceneRepository.save_scene(scene)


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
