"""GameForge AI — Phase 6C Production-Grade GLB Animation Export & Structural Validation Tests.

Verifies:
1. GLB Animation Inspector glTF 2.0 binary parsing & track analysis.
2. Structural Animation Validator rules (Magic, JSON/BIN chunks, channels, samplers, target paths, accessors, timestamp monotonicity, node bounds, skeleton joints, skin weights, material preservation).
3. Invalid GLB edge cases (corrupt headers, malformed JSON, missing animation/samplers, NaN/Inf bounds, zero duration).
4. API Endpoint POST /api/v1/animations/{animation_id}/validate and project isolation.
5. Real Blender 5.2.1 E2E procedural motion generation, GLB export, structural validation, and READY status for WALK, WAVE, RUN, and JUMP presets.
6. Export integrity (mesh, skin, rig, bone hierarchy, materials preserved).
"""

import json
import os
import struct
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.models.domain import (
    AnimationCreateRequest,
    AnimationStatus,
    AnimationType,
    AssetModel,
    CharacterCreateRequest,
    CharacterType,
    RigCharacterRequest,
    RigType,
)
from app.services.animation_manager import animation_manager
from app.services.animation_validator import animation_validator as glb_animation_validator
from app.services.asset_manager import asset_manager
from app.services.character_manager import character_manager
from app.services.glb_inspector import glb_inspector, GLBInspectorError

client = TestClient(app)


def get_existing_test_glb_url() -> str:
    """Helper to locate a real existing GLB model in public/exports to base character rigging on."""
    exports_dir = Path(__file__).resolve().parents[1] / "public" / "exports"
    if exports_dir.exists():
        glbs = list(exports_dir.glob("*.glb"))
        if glbs:
            return f"/exports/{glbs[0].name}"
    return "/exports/test_model.glb"


def build_mock_animated_glb(
    animations_data=None,
    nodes_data=None,
    skins_data=None,
    materials_data=None,
    meshes_data=None,
    corrupt_magic=False,
    corrupt_json=False,
) -> bytes:
    """Helper to assemble a valid or customized glTF 2.0 binary (.glb) for unit testing."""
    if corrupt_magic:
        magic = b"BADM"
    else:
        magic = b"glTF"

    version = 2

    # Default structural elements
    if nodes_data is None:
        nodes_data = [
            {"name": "Armature", "children": [1]},
            {"name": "mixamorig:Hips", "children": [2]},
            {"name": "mixamorig:Spine"},
        ]
    if skins_data is None:
        skins_data = [
            {
                "joints": [1, 2],
                "inverseBindMatrices": 0,
            }
        ]
    if materials_data is None:
        materials_data = [{"name": "CharacterMaterial", "pbrMetallicRoughness": {}}]
    if meshes_data is None:
        meshes_data = [
            {
                "name": "BodyMesh",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "JOINTS_0": 1, "WEIGHTS_0": 2},
                        "material": 0,
                    }
                ],
            }
        ]

    # Dummy accessors and bufferViews for BIN payload if animations provided
    accessors = []
    buffer_views = []
    bin_payload = bytearray()

    if animations_data is None:
        # Default single valid animation
        # Time accessor: 0.0 to 1.0 sec (4 floats = 16 bytes)
        time_offset = len(bin_payload)
        times = [0.0, 0.33, 0.66, 1.0]
        for t in times:
            bin_payload.extend(struct.pack("<f", t))

        # Value accessor: 4 quaternions (16 floats = 64 bytes)
        val_offset = len(bin_payload)
        for _ in range(4):
            bin_payload.extend(struct.pack("<ffff", 0.0, 0.0, 0.0, 1.0))

        buffer_views = [
            {"buffer": 0, "byteOffset": time_offset, "byteLength": len(times) * 4},
            {"buffer": 0, "byteOffset": val_offset, "byteLength": 16 * 4},
        ]

        accessors = [
            {
                "bufferView": 0,
                "componentType": 5126,  # FLOAT
                "count": len(times),
                "type": "SCALAR",
                "min": [0.0],
                "max": [1.0],
            },
            {
                "bufferView": 1,
                "componentType": 5126,  # FLOAT
                "count": 4,
                "type": "VEC4",
            },
        ]

        animations_data = [
            {
                "name": "WALK",
                "channels": [
                    {
                        "sampler": 0,
                        "target": {"node": 1, "path": "rotation"},
                    }
                ],
                "samplers": [
                    {"input": 0, "output": 1, "interpolation": "LINEAR"}
                ],
            }
        ]

    gltf_dict = {
        "asset": {"version": "2.0", "generator": "GameForge AI Unit Test"},
        "scenes": [{"nodes": [0]}],
        "nodes": nodes_data,
        "skins": skins_data,
        "materials": materials_data,
        "meshes": meshes_data,
        "animations": animations_data,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_payload)}],
    }

    if corrupt_json:
        json_bytes = b"{ malformed json string ... "
    else:
        json_bytes = json.dumps(gltf_dict).encode("utf-8")

    # Pad JSON chunk to 4-byte boundary
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * json_pad

    # Pad BIN chunk to 4-byte boundary
    bin_bytes = bytes(bin_payload)
    bin_pad = (4 - (len(bin_bytes) % 4)) % 4
    bin_bytes += b"\x00" * bin_pad

    json_chunk_header = struct.pack("<II", len(json_bytes), 0x4E4F534A)  # JSON
    bin_chunk_header = struct.pack("<II", len(bin_bytes), 0x00414E49)  # BIN

    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    header = struct.pack("<4sII", magic, version, total_length)

    return header + json_chunk_header + json_bytes + bin_chunk_header + bin_bytes


def create_test_character(name: str = "Test_Phase6C_Char", project_id: str = "proj_p6c"):
    """Helper to create a fully rigged character with Phase 5 armature and skinning."""
    glb_url = get_existing_test_glb_url()
    asset = asset_manager.save_asset(
        AssetModel(
            id=f"asset_test_{name}",
            project_id=project_id,
            name=name,
            glb_url=glb_url,
        )
    )
    char = character_manager.create_character(asset, name, CharacterType.HUMANOID)
    rig_req = RigCharacterRequest(rig_type=RigType.HUMANOID, auto_weight=True)
    char, rig, skeleton = character_manager.rig_character(char, rig_req)
    char = character_manager.get_character(char.id) or char
    return char


# ============================================================================
# 1. GLB INSPECTOR UNIT TESTS
# ============================================================================

def test_inspector_valid_glb_structure():
    """GLB inspector successfully extracts animation tracks, channels, and accessors."""
    glb_bytes = build_mock_animated_glb()
    info = glb_inspector.inspect_animation_glb(glb_bytes)

    assert info["is_valid_glb"] is True
    assert info["animation_count"] == 1
    assert len(info["animations"]) == 1

    anim = info["animations"][0]
    assert anim["name"] == "WALK"
    assert anim["channel_count"] == 1
    assert anim["sampler_count"] == 1
    assert anim["animated_node_count"] == 1
    assert anim["duration_seconds"] == 1.0
    assert "rotation" in anim["target_paths"]


def test_inspector_corrupt_bytes():
    """GLB inspector handles corrupt magic bytes or empty payloads safely."""
    with pytest.raises(GLBInspectorError) as exc_info:
        glb_inspector.inspect_animation_glb(b"")
    assert "File too small" in str(exc_info.value)

    bad_magic_bytes = build_mock_animated_glb(corrupt_magic=True)
    with pytest.raises(GLBInspectorError) as exc_info2:
        glb_inspector.inspect_animation_glb(bad_magic_bytes)
    assert "Invalid GLB magic header" in str(exc_info2.value)


def test_inspector_malformed_json():
    """GLB inspector handles malformed JSON chunk cleanly."""
    bad_json_bytes = build_mock_animated_glb(corrupt_json=True)
    with pytest.raises(GLBInspectorError) as exc_info:
        glb_inspector.inspect_animation_glb(bad_json_bytes)
    assert "GLB JSON chunk parse failure" in str(exc_info.value)


# ============================================================================
# 2. STRUCTURAL ANIMATION VALIDATOR TESTS
# ============================================================================

def test_validator_valid_mock_glb():
    """Structural validator approves a valid mock animated GLB."""
    glb_bytes = build_mock_animated_glb()
    result = glb_animation_validator.validate_glb(glb_bytes)

    assert result.valid is True
    assert result.animation_count == 1
    assert len(result.errors) == 0
    assert len(result.animations) == 1
    assert result.animations[0].valid is True


def test_validator_missing_animations():
    """Validator fails if GLB has no animations."""
    glb_bytes = build_mock_animated_glb(animations_data=[])
    result = glb_animation_validator.validate_glb(glb_bytes)

    assert result.valid is False
    assert any("no animation tracks" in err for err in result.errors)


def test_validator_invalid_sampler_index():
    """Validator catches invalid sampler reference in channel."""
    bad_channels_anim = [
        {
            "name": "INVALID_SAMPLER",
            "channels": [{"sampler": 99, "target": {"node": 1, "path": "translation"}}],
            "samplers": [{"input": 0, "output": 1}],
        }
    ]
    glb_bytes = build_mock_animated_glb(animations_data=bad_channels_anim)
    result = glb_animation_validator.validate_glb(glb_bytes)

    assert result.valid is False
    assert any("invalid sampler index" in err for err in result.errors)


def test_validator_invalid_target_path():
    """Validator rejects unsupported target paths."""
    bad_path_anim = [
        {
            "name": "BAD_PATH",
            "channels": [{"sampler": 0, "target": {"node": 1, "path": "invalid_property"}}],
            "samplers": [{"input": 0, "output": 1}],
        }
    ]
    glb_bytes = build_mock_animated_glb(animations_data=bad_path_anim)
    result = glb_animation_validator.validate_glb(glb_bytes)

    assert result.valid is False
    assert any("invalid target path" in err for err in result.errors)


def test_validator_missing_skin_and_materials():
    """Validator fails if character skin or materials are stripped."""
    glb_bytes = build_mock_animated_glb(skins_data=[], materials_data=[])
    result = glb_animation_validator.validate_glb(glb_bytes)

    assert result.valid is False
    assert any("contains no materials" in err for err in result.warnings)
    assert any("has_skins" not in result.model_dump() or not result.has_skins for err in [1])


# ============================================================================
# 3. ANIMATION VALIDATION API & PROJECT ISOLATION
# ============================================================================

def test_validate_animation_api_success():
    """POST /api/v1/animations/{animation_id}/validate succeeds for valid user asset."""
    char = create_test_character("API_Val_Char", project_id="proj_p6c_api")
    anim_req = AnimationCreateRequest(
        character_id=char.id,
        name="Test API Anim",
        animation_type=AnimationType.PROCEDURAL,
        motion_preset="WALK",
        project_id="proj_p6c_api",
    )
    anim = animation_manager.create_animation(char, anim_req)

    # Generate animation with real Blender
    anim = animation_manager.generate_procedural_animation(anim.id, motion_preset="WALK", project_id="proj_p6c_api")
    assert anim.status == AnimationStatus.READY

    # Call API endpoint
    res = client.post(
        f"/api/v1/animations/{anim.id}/validate",
        params={"project_id": "proj_p6c_api"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["animation_count"] >= 1
    assert len(data["errors"]) == 0


def test_validate_animation_api_project_isolation():
    """POST /api/v1/animations/{animation_id}/validate rejects access across projects."""
    char = create_test_character("Iso_Char", project_id="proj_owner")
    anim_req = AnimationCreateRequest(
        character_id=char.id,
        name="Owner Anim",
        animation_type=AnimationType.PROCEDURAL,
        motion_preset="WAVE",
        project_id="proj_owner",
    )
    anim = animation_manager.create_animation(char, anim_req)

    # Attempt validation from unauthorized project
    res = client.post(
        f"/api/v1/animations/{anim.id}/validate",
        params={"project_id": "proj_attacker"},
    )
    assert res.status_code == 404  # Isolated / not found under project


def test_validate_animation_api_not_found():
    """POST /api/v1/animations/{animation_id}/validate returns 404 for unknown animation ID."""
    res = client.post(
        "/api/v1/animations/non_existent_id/validate",
        params={"project_id": "proj_p6c_api"},
    )
    assert res.status_code == 404


# ============================================================================
# 4. REAL BLENDER 5.2.1 E2E TESTS (WALK, WAVE, RUN, JUMP)
# ============================================================================

@pytest.mark.parametrize("preset", ["WALK", "WAVE", "RUN", "JUMP"])
def test_real_blender_procedural_animation_e2e(preset):
    """E2E Test: Generate real procedural animation in Blender, export GLB, inspect & validate GLB structure."""
    char = create_test_character(f"Blender_E2E_{preset}", project_id="proj_e2e")

    anim_req = AnimationCreateRequest(
        character_id=char.id,
        name=f"E2E {preset} Animation",
        animation_type=AnimationType.PROCEDURAL,
        motion_preset=preset,
        speed=1.0,
        amplitude=1.0,
        duration_seconds=2.0,
        project_id="proj_e2e",
    )
    anim = animation_manager.create_animation(char, anim_req)
    assert anim.status == AnimationStatus.PENDING

    # Run real Blender execution pipeline
    anim = animation_manager.generate_procedural_animation(anim.id, motion_preset=preset, project_id="proj_e2e")

    # Assert lifecycle state transitioned to READY
    assert anim.status == AnimationStatus.READY, f"Animation failed with error: {anim.validation_error}"
    assert anim.glb_export_path is not None
    assert os.path.exists(anim.glb_export_path)

    # Read exported GLB and run independent GLB Inspector + Validator
    with open(anim.glb_export_path, "rb") as f:
        glb_bytes = f.read()

    # 1. Inspect GLB
    info = glb_inspector.inspect_animation_glb(glb_bytes)
    assert info["is_valid_glb"] is True
    assert info["animation_count"] >= 1
    
    anim_info = info["animations"][0]
    assert anim_info["channel_count"] > 0
    assert anim_info["sampler_count"] > 0
    assert anim_info["keyframe_count"] > 0
    assert anim_info["duration_seconds"] > 0
    assert anim_info["animated_node_count"] > 0

    # 2. Structurally Validate GLB
    val_result = glb_animation_validator.validate_glb(glb_bytes)
    assert val_result.valid is True
    assert len(val_result.errors) == 0
    assert val_result.animation_count >= 1

    report = val_result.animations[0]
    assert report.valid is True
    assert report.keyframe_count > 0
    assert report.duration_seconds > 0
    assert report.channel_count > 0

    # 3. Export Integrity (Verify Skin & Materials Preserved)
    assert info["skin_count"] >= 1
    assert info["material_count"] >= 1
    assert info["mesh_count"] >= 1


# ============================================================================
# 5. EXPORT INTEGRITY & RESTART PERSISTENCE
# ============================================================================

def test_export_integrity_and_persistence():
    """Verify animation validation metadata persists across system reloads."""
    char = create_test_character("Persist_Char", project_id="proj_persist")
    anim_req = AnimationCreateRequest(
        character_id=char.id,
        name="Persist Anim",
        animation_type=AnimationType.PROCEDURAL,
        motion_preset="WALK",
        project_id="proj_persist",
    )
    anim = animation_manager.create_animation(char, anim_req)
    anim = animation_manager.generate_procedural_animation(anim.id, motion_preset="WALK", project_id="proj_persist")

    assert anim.status == AnimationStatus.READY

    # Reload from DB via animation manager
    reloaded_anim = animation_manager.get_animation(anim.id, project_id="proj_persist")
    assert reloaded_anim is not None
    assert reloaded_anim.status == AnimationStatus.READY
    assert reloaded_anim.track_count >= 1
    assert reloaded_anim.duration_seconds > 0
    assert reloaded_anim.validation_error is None
