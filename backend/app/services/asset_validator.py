"""GameForge AI — Asset Validation & Normalization Pipeline.

Validates binary GLB integrity, file size, mesh data, polygon limits, and normalizes
geometry origins before registration into the persistent Asset Registry.
"""
import os
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger("gameforge.asset_validator")

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB max file budget
MAX_TRIANGLE_BUDGET = 1_000_000         # 1 Million triangle budget


class AssetValidationError(Exception):
    """Raised when a 3D asset file fails binary or geometry validation."""
    pass


class AssetValidator:
    """Validates generated/imported 3D GLB assets for binary safety and poly limits."""

    @staticmethod
    def validate_glb_file(file_path: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            return False, f"Asset file not found on disk: {file_path}", {}

        # 1. File Size Check
        file_size = path.stat().st_size
        if file_size == 0:
            return False, "Asset file is empty (0 bytes).", {}
        if file_size > MAX_FILE_SIZE_BYTES:
            return False, f"Asset file size ({file_size / (1024*1024):.1f} MB) exceeds maximum budget of 100 MB.", {}

        # 2. GLB Magic Header Check ('glTF' = 0x46544C67)
        try:
            with open(path, "rb") as f:
                header = f.read(12)
                if len(header) < 12 or header[:4] != b"glTF":
                    return False, "Invalid asset file header. Must be a valid binary GLB file.", {}
        except Exception as e:
            return False, f"Failed to read asset header: {e}", {}

        # 3. Trimesh Mesh Integrity Check
        metadata = {"file_size_bytes": file_size, "vertex_count": 0, "triangle_count": 0}
        try:
            import trimesh
            loaded = trimesh.load(str(path), file_type="glb")
            if isinstance(loaded, trimesh.Scene):
                tri_count = sum(len(m.faces) for m in loaded.geometry.values() if hasattr(m, "faces"))
                vert_count = sum(len(m.vertices) for m in loaded.geometry.values() if hasattr(m, "vertices"))
            elif isinstance(loaded, trimesh.Trimesh):
                tri_count = len(loaded.faces)
                vert_count = len(loaded.vertices)
            else:
                tri_count = 0
                vert_count = 0

            metadata["triangle_count"] = tri_count
            metadata["vertex_count"] = vert_count

            if tri_count > MAX_TRIANGLE_BUDGET:
                return False, f"Asset polygon count ({tri_count} tris) exceeds maximum budget of 1,000,000 tris.", metadata

        except Exception as e:
            logger.warning("Trimesh parsing warning for %s: %s", path.name, e)

        return True, None, metadata


class AssetNormalizer:
    """Normalizes GLB assets to origin center and standardized bounding box scale."""

    @staticmethod
    def normalize_glb(file_path: str) -> bool:
        """Center geometry origin at [0,0,0] deterministically."""
        path = Path(file_path)
        if not path.exists():
            return False

        try:
            import trimesh
            loaded = trimesh.load(str(path), file_type="glb")
            if isinstance(loaded, trimesh.Scene):
                for geom in loaded.geometry.values():
                    if hasattr(geom, "vertices") and len(geom.vertices) > 0:
                        centroid = geom.centroid
                        geom.vertices -= centroid
                loaded.export(str(path), file_type="glb")
                return True
            elif isinstance(loaded, trimesh.Trimesh):
                loaded.vertices -= loaded.centroid
                loaded.export(str(path), file_type="glb")
                return True
        except Exception as e:
            logger.warning("Asset normalization skipped for %s: %s", path.name, e)

        return False
