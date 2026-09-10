"""GameForge AI — Provider-Agnostic Asset Generation Architecture.

Defines the core AssetGenerationProvider interface and normalized result models.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.domain import AssetGenerationRequest


class AssetGenerationResult(BaseModel):
    """Normalized response returned by any 3D Asset Generation Provider."""
    success: bool
    provider_name: str
    provider_asset_id: Optional[str] = None
    glb_file_path: Optional[str] = None
    glb_url: Optional[str] = None
    vertex_count: int = 0
    triangle_count: int = 0
    error_message: Optional[str] = None
    is_fallback: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetGenerationProvider(ABC):
    """Abstract Base Class for all GameForge 3D Asset Generation Providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier string."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider API keys or local dependencies are configured."""
        pass

    @abstractmethod
    async def generate_asset(self, request: AssetGenerationRequest, job_id: str) -> AssetGenerationResult:
        """Generate a 3D asset from a structured normalized request."""
        pass
