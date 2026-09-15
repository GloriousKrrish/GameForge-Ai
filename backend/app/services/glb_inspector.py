"""GameForge AI — GLB Structural Binary Inspector.

Parses binary GLB (glTF 2.0) headers and JSON chunks to structurally inspect
meshes, materials, skins, armatures, and node hierarchies without requiring full 3D rendering engines.
"""
import json
import os
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional


class GLBInspectorError(ValueError):
    pass


class GLBInspector:
    """Inspects GLB binary files for glTF 2.0 compliance, skins, armatures, and materials."""

    @staticmethod
    def inspect(file_path: str) -> Dict[str, Any]:
        p = Path(file_path)
        if not p.exists():
            raise GLBInspectorError(f"GLB file path '{file_path}' does not exist.")

        with open(p, "rb") as f:
            data = f.read()

        if len(data) < 20:
            raise GLBInspectorError("File too small to be a valid GLB container.")

        # Header: magic (4 bytes), version (4 bytes), length (4 bytes)
        magic, version, length = struct.unpack("<4sII", data[:12])
        if magic != b"glTF":
            raise GLBInspectorError(f"Invalid GLB magic header: {magic}. Expected b'glTF'.")

        if version != 2:
            raise GLBInspectorError(f"Unsupported glTF version: {version}. Expected 2.")

        # Chunk 0 Header: chunk_length (4 bytes), chunk_type (4 bytes)
        chunk_len, chunk_type = struct.unpack("<II", data[12:20])
        # 0x4E4F534A is ASCII "JSON"
        if chunk_type != 0x4E4F534A:
            raise GLBInspectorError(f"First chunk type is {hex(chunk_type)}, expected JSON (0x4e4f534a).")

        json_bytes = data[20 : 20 + chunk_len]
        try:
            gltf_json = json.loads(json_bytes.decode("utf-8"))
        except Exception as exc:
            raise GLBInspectorError(f"Failed to parse GLB JSON chunk: {exc}") from exc

        skins = gltf_json.get("skins", [])
        nodes = gltf_json.get("nodes", [])
        meshes = gltf_json.get("meshes", [])
        materials = gltf_json.get("materials", [])

        nodes_with_skins = []
        for idx, node in enumerate(nodes):
            if "skin" in node:
                nodes_with_skins.append({
                    "index": idx,
                    "name": node.get("name", f"Node_{idx}"),
                    "skin_index": node["skin"],
                    "mesh_index": node.get("mesh"),
                })

        material_names = [mat.get("name", f"Material_{i}") for i, mat in enumerate(materials)]

        return {
            "file_path": str(p),
            "file_size_bytes": len(data),
            "is_valid_glb": True,
            "version": version,
            "json_chunk_bytes": chunk_len,
            "skin_count": len(skins),
            "has_skins": len(skins) > 0,
            "mesh_count": len(meshes),
            "node_count": len(nodes),
            "material_count": len(materials),
            "materials": material_names,
            "nodes_with_skins": nodes_with_skins,
            "raw_json": gltf_json,
        }


glb_inspector = GLBInspector()
