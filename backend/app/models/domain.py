"""GameForge AI — Core Domain Data Models.

Defines the clean domain contracts for Project, Scene, SceneObject, Camera, Light, Material, and Artifact.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


from enum import Enum

class AlphaMode(str, Enum):
    OPAQUE = "OPAQUE"
    MASK = "MASK"
    BLEND = "BLEND"


class TextureType(str, Enum):
    BASE_COLOR = "BASE_COLOR"
    ROUGHNESS = "ROUGHNESS"
    METALLIC = "METALLIC"
    NORMAL = "NORMAL"
    EMISSION = "EMISSION"
    AO = "AO"


class AssetSourceType(str, Enum):
    GENERATED = "GENERATED"
    IMPORTED = "IMPORTED"
    PROCEDURAL = "PROCEDURAL"
    SYSTEM = "SYSTEM"


class AssetStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    FAILED = "FAILED"


class AssetModel(BaseModel):
    id: str
    project_id: str = "proj_default"
    name: str
    description: Optional[str] = None
    source_type: AssetSourceType = AssetSourceType.GENERATED
    provider: str = "DETERMINISTIC_FALLBACK"
    provider_asset_id: Optional[str] = None
    glb_url: str
    format: str = "glb"
    mime_type: str = "model/gltf-binary"
    thumbnail_path: Optional[str] = None
    status: AssetStatus = AssetStatus.READY
    generation_prompt: Optional[str] = None
    vertex_count: int = 0
    triangle_count: int = 0
    material_count: int = 1
    animation_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Texture(BaseModel):
    id: str
    name: str
    file_url: str
    type: TextureType = TextureType.BASE_COLOR
    width: Optional[int] = None
    height: Optional[int] = None
    color_space: str = "sRGB"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TransformModel(BaseModel):
    position: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])


class MaterialModel(BaseModel):
    color: str = "#E8B4B8"
    metallic: float = 0.4
    roughness: float = 0.5


class Material(BaseModel):
    id: str
    name: str
    base_color: List[float] = Field(default_factory=lambda: [0.91, 0.71, 0.72])  # RGB [0..1]
    metallic: float = 0.4
    roughness: float = 0.5
    emission_color: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    emission_strength: float = 0.0
    opacity: float = 1.0
    alpha_mode: AlphaMode = AlphaMode.OPAQUE
    double_sided: bool = False
    texture_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SceneObject(BaseModel):
    id: str
    name: str
    object_type: str  # CUBE, SPHERE, MESH, CAMERA, LIGHT
    transform: TransformModel = Field(default_factory=TransformModel)
    material: Optional[MaterialModel] = None
    material_id: Optional[str] = None
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


class MaterialCreateRequest(BaseModel):
    name: str
    base_color: Optional[List[float]] = None
    metallic: Optional[float] = None
    roughness: Optional[float] = None
    emission_color: Optional[List[float]] = None
    emission_strength: Optional[float] = None
    opacity: Optional[float] = None
    alpha_mode: Optional[AlphaMode] = None
    double_sided: Optional[bool] = None


class MaterialUpdateRequest(BaseModel):
    name: Optional[str] = None
    base_color: Optional[List[float]] = None
    metallic: Optional[float] = None
    roughness: Optional[float] = None
    emission_color: Optional[List[float]] = None
    emission_strength: Optional[float] = None
    opacity: Optional[float] = None
    alpha_mode: Optional[AlphaMode] = None
    double_sided: Optional[bool] = None


class AssignMaterialRequest(BaseModel):
    material_id: str


class AssetGenerationRequest(BaseModel):
    prompt: str
    style: str = "realistic"  # realistic, stylized, low-poly
    quality: str = "standard"  # draft, standard, high
    poly_budget: int = 50000
    target_format: str = "glb"
    target_use: str = "game_asset"
    generate_materials: bool = True
    project_id: str = "proj_default"


class InstantiateAssetRequest(BaseModel):
    asset_id: str
    name: Optional[str] = None
    position: Optional[List[float]] = None
    rotation: Optional[List[float]] = None
    scale: Optional[List[float]] = None
