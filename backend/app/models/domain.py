"""GameForge AI — Core Domain Data Models.

Defines the clean domain contracts for Project, Scene, SceneObject, Camera, Light, Material, and Artifact.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class TransformModel(BaseModel):
    position: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])


class MaterialModel(BaseModel):
    color: str = "#E8B4B8"
    metallic: float = 0.4
    roughness: float = 0.5


class SceneObject(BaseModel):
    id: str
    name: str
    object_type: str  # CUBE, SPHERE, MESH, CAMERA, LIGHT
    transform: TransformModel = Field(default_factory=TransformModel)
    material: Optional[MaterialModel] = None
    parent_id: Optional[str] = None
    visible: bool = True
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CameraModel(BaseModel):
    id: str
    name: str = "Main_Camera"
    location: List[float] = Field(default_factory=lambda: [4.0, -4.0, 3.0])
    rotation: List[float] = Field(default_factory=lambda: [60.0, 0.0, 45.0])
    fov: float = 50.0


class LightModel(BaseModel):
    id: str
    name: str = "Sun_Light"
    light_type: str = "SUN"  # POINT, SUN, SPOT, AREA
    energy: float = 1000.0
    location: List[float] = Field(default_factory=lambda: [5.0, 5.0, 10.0])


class Scene(BaseModel):
    id: str
    project_id: str
    name: str = "Main Scene"
    objects: List[SceneObject] = Field(default_factory=list)
    cameras: List[CameraModel] = Field(default_factory=list)
    lights: List[LightModel] = Field(default_factory=list)
    environment: Dict[str, Any] = Field(default_factory=lambda: {"background_color": "#111827"})
    active_asset_url: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Project(BaseModel):
    id: str
    name: str = "Untitled GameForge Project"
    active_scene_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TransformUpdateRequest(BaseModel):
    object_name: str
    position: Optional[List[float]] = None
    rotation: Optional[List[float]] = None
    scale: Optional[List[float]] = None


class SceneObjectCreateRequest(BaseModel):
    name: str
    object_type: str = "CUBE"
    position: Optional[List[float]] = None
    rotation: Optional[List[float]] = None
    scale: Optional[List[float]] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None


class SceneObjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    position: Optional[List[float]] = None
    rotation: Optional[List[float]] = None
    scale: Optional[List[float]] = None
    visible: Optional[bool] = None
    parent_id: Optional[str] = None
    color: Optional[str] = None


class ParentRequest(BaseModel):
    child_id: str
    parent_id: str


class UnparentRequest(BaseModel):
    child_id: str
