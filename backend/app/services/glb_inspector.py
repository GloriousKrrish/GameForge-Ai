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
    def inspect(file_path_or_bytes: Any) -> Dict[str, Any]:
        if isinstance(file_path_or_bytes, bytes):
            data = file_path_or_bytes
            file_path_str = "<memory_buffer>"
        else:
            p = Path(file_path_or_bytes)
            if not p.exists():
                raise GLBInspectorError(f"GLB file path '{file_path_or_bytes}' does not exist.")
            file_path_str = str(p)
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
            raise GLBInspectorError(f"GLB JSON chunk parse failure: {exc}") from exc

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
            "file_path": file_path_str,
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
            "raw_bytes": data,
        }

    @classmethod
    def inspect_animation_glb(cls, file_path_or_bytes: Any) -> Dict[str, Any]:
        """Deeply inspect binary GLB glTF 2.0 container, including binary accessors, keyframes, animations, skins, and materials."""
        import math
        base_info = cls.inspect(file_path_or_bytes)
        gltf_json = base_info.get("raw_json", {})
        raw = base_info.get("raw_bytes", b"")

        # Read BIN chunk if present
        bin_data = b""
        json_chunk_len = base_info["json_chunk_bytes"]
        bin_chunk_offset = 20 + json_chunk_len
        if len(raw) >= bin_chunk_offset + 8:
            bin_chunk_len, bin_chunk_type = struct.unpack("<II", raw[bin_chunk_offset : bin_chunk_offset + 8])
            bin_data = raw[bin_chunk_offset + 8 : bin_chunk_offset + 8 + bin_chunk_len]

        accessors = gltf_json.get("accessors", [])
        buffer_views = gltf_json.get("bufferViews", [])
        animations = gltf_json.get("animations", [])

        def read_accessor_floats(accessor_idx: int) -> List[float]:
            if accessor_idx < 0 or accessor_idx >= len(accessors):
                return []
            acc = accessors[accessor_idx]
            bv_idx = acc.get("bufferView")
            if bv_idx is None or bv_idx < 0 or bv_idx >= len(buffer_views):
                return []
            bv = buffer_views[bv_idx]
            byte_offset = (bv.get("byteOffset", 0)) + (acc.get("byteOffset", 0))
            count = acc.get("count", 0)
            comp_type = acc.get("componentType", 5126)
            acc_type = acc.get("type", "SCALAR")

            num_components = 1
            if acc_type == "VEC2":
                num_components = 2
            elif acc_type == "VEC3":
                num_components = 3
            elif acc_type == "VEC4":
                num_components = 4
            elif acc_type == "MAT4":
                num_components = 16

            total_floats = count * num_components
            end_offset = byte_offset + total_floats * 4
            if end_offset > len(bin_data):
                return []
            if comp_type == 5126:  # FLOAT
                return list(struct.unpack(f"<{total_floats}f", bin_data[byte_offset:end_offset]))
            return []

        inspected_anims = []
        for i, anim in enumerate(animations):
            anim_name = anim.get("name", f"Animation_{i}")
            channels = anim.get("channels", [])
            samplers = anim.get("samplers", [])

            animated_nodes = set()
            target_paths = set()
            total_keyframes = 0
            min_time = float("inf")
            max_time = float("-inf")

            for ch in channels:
                target = ch.get("target", {})
                node_idx = target.get("node")
                path = target.get("path")
                if node_idx is not None:
                    animated_nodes.add(node_idx)
                if path:
                    target_paths.add(path)

                sampler_idx = ch.get("sampler")
                if sampler_idx is not None and 0 <= sampler_idx < len(samplers):
                    smp = samplers[sampler_idx]
                    inp_idx = smp.get("input")
                    if inp_idx is not None:
                        t_vals = read_accessor_floats(inp_idx)
                        if t_vals:
                            total_keyframes += len(t_vals)
                            min_time = min(min_time, min(t_vals))
                            max_time = max(max_time, max(t_vals))

            duration = max(0.0, max_time - min_time) if math.isfinite(max_time) and math.isfinite(min_time) and min_time != float("inf") else 0.0

            inspected_anims.append({
                "index": i,
                "name": anim_name,
                "channel_count": len(channels),
                "sampler_count": len(samplers),
                "keyframe_count": total_keyframes,
                "animated_node_count": len(animated_nodes),
                "target_paths": sorted(list(target_paths)),
                "min_time": min_time if math.isfinite(min_time) and min_time != float("inf") else 0.0,
                "max_time": max_time if math.isfinite(max_time) and max_time != float("-inf") else 0.0,
                "duration_seconds": duration,
                "raw_channels": channels,
                "raw_samplers": samplers,
            })

        base_info["animation_count"] = len(animations)
        base_info["has_animations"] = len(animations) > 0
        base_info["animations"] = inspected_anims
        return base_info


glb_inspector = GLBInspector()
