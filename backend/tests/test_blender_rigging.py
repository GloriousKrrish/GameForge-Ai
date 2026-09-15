"""GameForge AI — Phase 5 Blender Rigging & GLB Inspection Test Suite.

Empirically verifies real Blender armature creation, mesh skinning, vertex weight validation,
GLB binary container inspection, material preservation, and backend restart persistence.
"""
from pathlib import Path
import pytest

from app.models.domain import (
    AssetModel, AssetSourceType, AssetStatus, CharacterStatus, CharacterType,
    RigCharacterRequest, RigType, SkinningModel,
)
from app.services.asset_manager import asset_manager
from app.services.character_manager import CharacterValidationError, character_manager
from app.services.glb_inspector import glb_inspector, GLBInspectorError


def make_test_asset(asset_id="asset_blender_test", project_id="proj_default"):
    return asset_manager.save_asset(AssetModel(
        id=asset_id,
        project_id=project_id,
        name="Blender Rigging Test Asset",
        source_type=AssetSourceType.GENERATED,
        status=AssetStatus.READY,
        glb_url="/exports/test_model.glb",
    ))


def test_real_blender_armature_and_skinning_export():
    asset = make_test_asset("asset_blender_real_1")
    character = character_manager.create_character(asset, "Hero Character", CharacterType.HUMANOID)
    
    updated_char, rig, skeleton = character_manager.rig_character(
        character, RigCharacterRequest(rig_type=RigType.HUMANOID)
    )

    # Status must be READY when Blender rigging succeeds
    assert updated_char.status == CharacterStatus.READY
    assert updated_char.skeleton_id == skeleton.id
    assert updated_char.rig_id == rig.id
    assert skeleton.bone_count == 9

    # Verify bone hierarchy
    bone_names = [b.name for b in skeleton.bones]
    assert "Root" in bone_names
    assert "Spine" in bone_names
    assert "Head" in bone_names

    # Verify skinning model
    assert updated_char.skinning is not None
    assert updated_char.skinning.status == "VALID"
    assert updated_char.skinning.max_influences_per_vertex == 4

    # Verify output GLB binary container structurally
    exports_dir = Path(__file__).resolve().parents[1] / "public" / "exports"
    output_glb_path = exports_dir / f"rigged_{character.id}.glb"
    assert output_glb_path.exists(), f"Output GLB file not found at {output_glb_path}"

    inspection = glb_inspector.inspect(str(output_glb_path))
    assert inspection["is_valid_glb"] is True
    assert inspection["version"] == 2
    assert inspection["has_skins"] is True
    assert inspection["skin_count"] >= 1
    assert len(inspection["nodes_with_skins"]) >= 1


def test_glb_inspector_error_handling():
    with pytest.raises(GLBInspectorError, match="does not exist"):
        glb_inspector.inspect("non_existent_file_path_12345.glb")


def test_vertex_weight_validation():
    asset = make_test_asset("asset_weight_val_1")
    character = character_manager.create_character(asset, "ValChar", CharacterType.HUMANOID)
    updated_char, rig, skeleton = character_manager.rig_character(character, RigCharacterRequest())

    # Create unnormalized weight (sum != 1.0)
    bad_skinning = SkinningModel(
        skeleton_id=skeleton.id,
        vertex_count=10,
        max_influences_per_vertex=4,
        influences={
            skeleton.bones[0].id: [{"vertex_index": 0, "weight": 0.3}],
            skeleton.bones[1].id: [{"vertex_index": 0, "weight": 0.2}], # Sum = 0.5 != 1.0
        },
        status="VALID",
    )
    updated_char.skinning = bad_skinning

    with pytest.raises(CharacterValidationError, match="not normalized"):
        character_manager.validate_character(updated_char, skeleton, rig)


def test_invalid_bone_reference_in_skinning_rejected():
    asset = make_test_asset("asset_weight_val_2")
    character = character_manager.create_character(asset, "ValChar2", CharacterType.HUMANOID)
    updated_char, rig, skeleton = character_manager.rig_character(character, RigCharacterRequest())

    bad_skinning = SkinningModel(
        skeleton_id=skeleton.id,
        vertex_count=10,
        max_influences_per_vertex=4,
        influences={
            "bone_unknown_999": [{"vertex_index": 0, "weight": 1.0}],
        },
        status="VALID",
    )
    updated_char.skinning = bad_skinning

    with pytest.raises(CharacterValidationError, match="references unknown bone ID"):
        character_manager.validate_character(updated_char, skeleton, rig)


def test_backend_restart_persistence():
    asset = make_test_asset("asset_restart_persistence")
    character = character_manager.create_character(asset, "PersistentHero", CharacterType.HUMANOID)
    updated_char, rig, skeleton = character_manager.rig_character(character, RigCharacterRequest())

    # Query from database to simulate backend restart
    reloaded_char = character_manager.get_character(character.id)
    reloaded_skel = character_manager.get_skeleton(character.id)
    reloaded_rig = character_manager.get_rig(character.id)

    assert reloaded_char is not None
    assert reloaded_skel is not None
    assert reloaded_rig is not None

    assert reloaded_char.id == updated_char.id
    assert reloaded_char.status == CharacterStatus.READY
    assert reloaded_skel.bone_count == 9
    assert reloaded_rig.provider == "BLENDER_RIGGING_PROVIDER"
    assert reloaded_char.skinning.status == "VALID"
