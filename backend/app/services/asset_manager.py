"""GameForge AI — Persistent SQLite Asset Manager.

Manages 3D Asset Registration, Query Filtering, and Persistence in SQLite.
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.db.database import db
from app.models.domain import AssetModel, AssetSourceType, AssetStatus

logger = logging.getLogger("gameforge.asset_manager")


class AssetManager:
    """Manages persistent SQLite Asset Registry."""

    def register_asset(
        self,
        name: str,
        glb_url: str,
        description: Optional[str] = None,
        source_type: AssetSourceType = AssetSourceType.GENERATED,
        provider: str = "DETERMINISTIC_FALLBACK",
        provider_asset_id: Optional[str] = None,
        generation_prompt: Optional[str] = None,
        vertex_count: int = 0,
        triangle_count: int = 0,
        material_count: int = 1,
        metadata: Optional[dict] = None,
        project_id: str = "proj_default",
    ) -> AssetModel:
        asset_id = f"asset_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        asset = AssetModel(
            id=asset_id,
            project_id=project_id,
            name=name,
            description=description,
            source_type=source_type,
            provider=provider,
            provider_asset_id=provider_asset_id,
            glb_url=glb_url,
            status=AssetStatus.READY,
            generation_prompt=generation_prompt,
            vertex_count=vertex_count,
            triangle_count=triangle_count,
            material_count=material_count,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO assets (id, name, type, glb_url, poly_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (asset.id, asset.name, asset.source_type.value, asset.glb_url, asset.triangle_count, asset.created_at)
            )

        logger.info("Asset registered in SQLite: %s (%s)", asset.name, asset.id)
        return asset

    def save_asset(self, asset: AssetModel) -> AssetModel:
        """Save a pre-constructed AssetModel instance into SQLite registry."""
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO assets (id, name, type, glb_url, poly_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (asset.id, asset.name, asset.source_type.value, asset.glb_url, asset.triangle_count, asset.created_at or datetime.now(timezone.utc).isoformat())
            )
        logger.info("Asset saved in SQLite: %s (%s)", asset.name, asset.id)
        return asset

    def get_asset(self, asset_id: str) -> Optional[AssetModel]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
            if row:
                return AssetModel(
                    id=row["id"],
                    project_id="proj_default",
                    name=row["name"],
                    source_type=AssetSourceType(row["type"]) if row["type"] in [e.value for e in AssetSourceType] else AssetSourceType.GENERATED,
                    provider="DETERMINISTIC_FALLBACK",
                    glb_url=row["glb_url"],
                    triangle_count=row["poly_count"] or 0,
                    created_at=row["created_at"],
                )
            return None

    def list_assets(
        self,
        project_id: Optional[str] = None,
        source_type: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> List[AssetModel]:
        with db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM assets ORDER BY created_at DESC").fetchall()
            assets = []
            for row in rows:
                s_type = AssetSourceType(row["type"]) if row["type"] in [e.value for e in AssetSourceType] else AssetSourceType.GENERATED
                if source_type and s_type.value != source_type:
                    continue
                assets.append(
                    AssetModel(
                        id=row["id"],
                        project_id="proj_default",
                        name=row["name"],
                        source_type=s_type,
                        provider="DETERMINISTIC_FALLBACK",
                        glb_url=row["glb_url"],
                        triangle_count=row["poly_count"] or 0,
                        created_at=row["created_at"],
                    )
                )
            return assets

    def delete_asset(self, asset_id: str) -> bool:
        with db.get_connection() as conn:
            cur = conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
            return cur.rowcount > 0


asset_manager = AssetManager()
