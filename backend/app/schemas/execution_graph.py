from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OperationType(str, Enum):
    """Registry of all allowed execution operations.
    Only operations listed here can be executed by the GameForge engine.
    """
    CREATE_CUBE = "CREATE_CUBE"
    CREATE_SPHERE = "CREATE_SPHERE"
    CREATE_CAMERA = "CREATE_CAMERA"
    CREATE_LIGHT = "CREATE_LIGHT"
    DELETE_OBJECT = "DELETE_OBJECT"
    MOVE_OBJECT = "MOVE_OBJECT"
    ROTATE_OBJECT = "ROTATE_OBJECT"
    SCALE_OBJECT = "SCALE_OBJECT"
    SET_MATERIAL = "SET_MATERIAL"
    DUPLICATE_OBJECT = "DUPLICATE_OBJECT"
    PARENT_OBJECT = "PARENT_OBJECT"
    UNPARENT_OBJECT = "UNPARENT_OBJECT"
    RENAME_OBJECT = "RENAME_OBJECT"
    HIDE_OBJECT = "HIDE_OBJECT"
    SHOW_OBJECT = "SHOW_OBJECT"
    EXPORT_GLB = "EXPORT_GLB"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ExecutionStep(BaseModel):
    id: str = Field(..., description="Unique ID for this step in the graph")
    type: OperationType = Field(..., description="Type of operation to perform")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Current execution status of this step")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the operation")
    error: Optional[str] = Field(default=None, description="Error message if step failed")


class ExecutionGraph(BaseModel):
    id: str = Field(..., description="Unique graph ID")
    version: str = Field(default="1.0", description="Execution Graph schema version")
    steps: List[ExecutionStep] = Field(..., description="Ordered list of execution steps")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional graph metadata")


class JobStatus(str, Enum):
    IDLE = "IDLE"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class GenerationJobResponse(BaseModel):
    id: str
    prompt: str
    status: JobStatus
    progress: float = 0.0
    current_step: Optional[str] = None
    execution_graph: Optional[ExecutionGraph] = None
    asset_url: Optional[str] = None
    asset_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language user prompt")
    execution_graph: Optional[ExecutionGraph] = Field(
        default=None,
        description="Optional pre-built execution graph. If omitted, the backend builds one from the prompt.",
    )


class AssetResponse(BaseModel):
    id: str
    name: str
    type: str = "model"
    glb_url: str
    thumbnail_url: Optional[str] = None
    poly_count: Optional[int] = None
    created_at: str


class ExportRequest(BaseModel):
    asset_id: str = Field(..., description="ID of the asset to export/download")
