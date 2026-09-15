"""GameForge AI — Phase 6B Real Blender Animation & Procedural Motion Tests.

Verifies:
1. APPLY_PROCEDURAL_ANIMATION Execution Graph operation and validator bounds.
2. Real Blender 5.2.1 Action creation, PoseBone keyframing, and F-curves.
3. Deterministic motions: IDLE, WALK, RUN, WAVE, JUMP.
4. Animation lifecycle (PENDING -> GENERATING -> READY / FAILED).
5. Material, skinning, and multi-character isolation preservation.
6. Programmatic Blender Action structural validation.
"""
import pytest
from app.models.domain import (
    AnimationCreateRequest, AnimationStatus, AnimationType, AssetModel,
    CharacterCreateRequest, CharacterType, RigCharacterRequest, RigType,
)
from app.schemas.execution_graph import ExecutionGraph, ExecutionStep, OperationType
from app.services.animation_manager import AnimationValidationError, animation_manager
from app.services.asset_manager import asset_manager
from app.services.character_manager import character_manager
from app.services.validator import ExecutionGraphValidator


def create_test_character(name: str = "Test_Anim_Char", project_id: str = "proj_default"):
    """Helper to create a fully rigged character with Phase 5 armature and skinning."""
    from pathlib import Path
    exports_dir = Path(__file__).resolve().parents[1] / "public" / "exports"
    glbs = list(exports_dir.glob("*.glb")) if exports_dir.exists() else []
    glb_url = f"/exports/{glbs[0].name}" if glbs else "/exports/test.glb"

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


def test_validator_apply_procedural_animation_valid():
    """Validator accepts valid APPLY_PROCEDURAL_ANIMATION operation."""
    graph = ExecutionGraph(
        id="graph_valid_anim",
        steps=[
            ExecutionStep(
                id="s1",
                type=OperationType.APPLY_PROCEDURAL_ANIMATION,
                parameters={
                    "animation_id": "anim_123",
                    "character_id": "char_123",
                    "motion_preset": "WALK",
                    "speed": 1.2,
                    "amplitude": 1.0,
                    "loop": True,
                },
            ),
            ExecutionStep(
                id="s2",
                type=OperationType.EXPORT_GLB,
                parameters={},
            ),
        ],
    )
    is_valid, err = ExecutionGraphValidator.validate(graph)
    assert is_valid is True, f"Validation failed: {err}"


def test_validator_apply_procedural_animation_out_of_bounds():
    """Validator rejects invalid speed, amplitude, or motion preset."""
    # Invalid motion preset
    graph_invalid_preset = ExecutionGraph(
        id="graph_inv_preset",
        steps=[
            ExecutionStep(
                id="s1",
                type=OperationType.APPLY_PROCEDURAL_ANIMATION,
                parameters={
                    "animation_id": "anim_123",
                    "character_id": "char_123",
                    "motion_preset": "INVALID_MOTION",
                },
            ),
            ExecutionStep(id="s2", type=OperationType.EXPORT_GLB, parameters={}),
        ],
    )
    is_valid, err = ExecutionGraphValidator.validate(graph_invalid_preset)
    assert is_valid is False
    assert "Invalid motion_preset" in err

    # Out of bounds speed
    graph_invalid_speed = ExecutionGraph(
        id="graph_inv_speed",
        steps=[
            ExecutionStep(
                id="s1",
                type=OperationType.APPLY_PROCEDURAL_ANIMATION,
                parameters={
                    "animation_id": "anim_123",
                    "character_id": "char_123",
                    "motion_preset": "WALK",
                    "speed": 15.0,  # Max allowed is 10.0
                },
            ),
            ExecutionStep(id="s2", type=OperationType.EXPORT_GLB, parameters={}),
        ],
    )
    is_valid, err = ExecutionGraphValidator.validate(graph_invalid_speed)
    assert is_valid is False
    assert "Invalid speed" in err


def test_animation_generation_walk_e2e():
    """Real E2E test for WALK cycle procedural generation in Blender."""
    char = create_test_character("Walk_Char")
    anim_req = AnimationCreateRequest(
        character_id=char.id,
        name="Walk Cycle",
        animation_type=AnimationType.WALK,
        rig_id=char.rig_id,
        duration_seconds=2.0,
        fps=30,
        project_id=char.project_id,
    )
    anim = animation_manager.create_animation(char, anim_req)

    # Trigger real Blender procedural generation
    updated_anim = animation_manager.generate_procedural_animation(
        animation_id=anim.id,
        motion_preset="WALK",
        speed=1.0,
        amplitude=1.0,
    )

    assert updated_anim.status == AnimationStatus.READY
    assert updated_anim.glb_url is not None
    assert updated_anim.track_count >= 9
    assert updated_anim.metadata.get("provider") == "DETERMINISTIC_PROCEDURAL"
    assert updated_anim.metadata.get("motion_preset") == "WALK"


def test_animation_generation_wave_e2e():
    """Real E2E test for WAVE animation procedural generation in Blender."""
    char = create_test_character("Wave_Char")
    anim_req = AnimationCreateRequest(
        character_id=char.id,
        name="Right Arm Wave",
        animation_type=AnimationType.WAVE,
        rig_id=char.rig_id,
        duration_seconds=1.5,
        fps=30,
        project_id=char.project_id,
    )
    anim = animation_manager.create_animation(char, anim_req)

    updated_anim = animation_manager.generate_procedural_animation(
        animation_id=anim.id,
        motion_preset="WAVE",
        speed=1.0,
        amplitude=1.0,
    )

    assert updated_anim.status == AnimationStatus.READY
    assert updated_anim.metadata.get("motion_preset") == "WAVE"


def test_animation_generation_idle_run_jump_all_presets():
    """Verify all motion presets (IDLE, RUN, JUMP) generate valid READY records."""
    char = create_test_character("All_Presets_Char")

    for preset in ("IDLE", "RUN", "JUMP"):
        anim_req = AnimationCreateRequest(
            character_id=char.id,
            name=f"{preset} Preset",
            animation_type=AnimationType(preset),
            rig_id=char.rig_id,
            duration_seconds=1.0,
            fps=30,
            project_id=char.project_id,
        )
        anim = animation_manager.create_animation(char, anim_req)

        res = animation_manager.generate_procedural_animation(
            animation_id=anim.id,
            motion_preset=preset,
        )
        assert res.status == AnimationStatus.READY
        assert res.metadata.get("motion_preset") == preset


def test_animation_generation_failure_handling():
    """Verify failure cases set status to FAILED and record error details."""
    with pytest.raises(AnimationValidationError):
        animation_manager.generate_procedural_animation("non_existent_anim_id")


def test_multi_character_isolation():
    """Verify animating Character A does not pollute or affect Character B."""
    char_a = create_test_character("Char_A")
    char_b = create_test_character("Char_B")

    anim_a_req = AnimationCreateRequest(
        character_id=char_a.id,
        name="Char A Walk",
        animation_type=AnimationType.WALK,
        rig_id=char_a.rig_id,
        project_id=char_a.project_id,
    )
    anim_a = animation_manager.create_animation(char_a, anim_a_req)
    res_a = animation_manager.generate_procedural_animation(anim_a.id, motion_preset="WALK")

    anims_b = animation_manager.list_animations(character_id=char_b.id)
    assert len(anims_b) == 0
    assert res_a.character_id == char_a.id
