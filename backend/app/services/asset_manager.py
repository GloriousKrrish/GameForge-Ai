"""GameForge AI — In-memory Asset Manager.
Tracks generated 3D assets with metadata. Persistence can be added later.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.schemas.execution_graph import AssetResponse


class AssetManager:
    """In-memory asset store. Will be replaced with database persistence later."""

    def __init__(self):
        self._assets: Dict[str, AssetResponse] = {}

    def register_asset(
        self,
        name: str,
        glb_url: str,
        asset_type: str = "model",
        poly_count: Optional[int] = None,
    ) -> AssetResponse:
        asset_id = f"asset_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        asset = AssetResponse(
            id=asset_id,
            name=name,
            type=asset_type,
            glb_url=glb_url,
            poly_count=poly_count,
            created_at=now,
        )
        self._assets[asset_id] = asset
        return asset

    def get_asset(self, asset_id: str) -> Optional[AssetResponse]:
        return self._assets.get(asset_id)

    def list_assets(self) -> List[AssetResponse]:
        return list(self._assets.values())


asset_manager = AssetManager()
