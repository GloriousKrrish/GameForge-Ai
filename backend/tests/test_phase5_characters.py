import asyncio

from app.models.domain import (
    AssetModel, AssetSourceType, AssetStatus, CharacterStatus, CharacterType,
    RigCharacterRequest, RigType,
)
from app.planners.deterministic import DeterministicPlanner
from app.schemas.execution_graph import ExecutionGraph, ExecutionStep, OperationType
from app.services.asset_manager import asset_manager
from app.services.character_manager import CharacterValidationError, character_manager
from app.services.validator import ExecutionGraphValidator


def make_asset(asset_id="asset_character_1", project_id="proj_default"):
    return asset_manager.save_asset(AssetModel(
        id=asset_id,
        project_id=project_id,
        name="Stylized Warrior",
        source_type=AssetSourceType.GENERATED,
        status=AssetStatus.READY,
        glb_url="/exports/warrior.glb",
    ))


def test_character_rig_skeleton_and_persistence():
    asset = make_asset()
    character = character_manager.create_character(asset, "Warrior", CharacterType.HUMANOID)
    updated, rig, skeleton = character_manager.rig_character(character, RigCharacterRequest(rig_type=RigType.HUMANOID))

    # When Blender is available → READY (full pipeline); when not → RIGGED (deterministic)
    assert updated.status in (CharacterStatus.RIGGED, CharacterStatus.READY), (
        f"Expected RIGGED or READY, got {updated.status}"
    )
    assert updated.asset_id == asset.id
    assert updated.rig_id == rig.id
    assert updated.skeleton_id == skeleton.id
    assert skeleton.bone_count == len(skeleton.bones)
    assert skeleton.bones[0].id == skeleton.root_bone_id
    assert character_manager.get_character(character.id).status in (CharacterStatus.RIGGED, CharacterStatus.READY)
    assert character_manager.get_skeleton(character.id).id == skeleton.id
    assert character_manager.get_rig(character.id).id == rig.id



def test_character_asset_project_scope():
    asset = make_asset(project_id="proj_a")
    character = character_manager.create_character(asset, "Scoped", CharacterType.CUSTOM)
    assert character.project_id == "proj_a"


def test_invalid_parent_reference_is_rejected():
    asset = make_asset()
    character = character_manager.create_character(asset, "Warrior", CharacterType.HUMANOID)
    _, _, skeleton = character_manager.rig_character(character, RigCharacterRequest())
    skeleton.bones[1].parent_id = "bone_unknown"
    try:
        character_manager.validate_character(character, skeleton, character_manager.get_rig(character.id))
    except CharacterValidationError as exc:
        assert "unknown parent" in str(exc)
    else:
        raise AssertionError("invalid parent reference was accepted")


def test_execution_graph_phase5_operations_are_registered_and_bounded():
    graph = ExecutionGraph(id="phase5_graph", steps=[
        ExecutionStep(id="rig", type=OperationType.RIG_CHARACTER, parameters={"character_id": "char_1", "rig_type": "HUMANOID"}),
        ExecutionStep(id="validate", type=OperationType.VALIDATE_CHARACTER, parameters={"character_id": "char_1"}),
        ExecutionStep(id="export", type=OperationType.EXPORT_GLB, parameters={}),
    ])
    valid, error = ExecutionGraphValidator.validate(graph)
    assert valid, error

    invalid = graph.model_copy(deep=True)
    invalid.steps[0].parameters["rig_type"] = "ARBITRARY"
    valid, error = ExecutionGraphValidator.validate(invalid)
    assert not valid
    assert "rig_type" in error


def test_planner_emits_structured_existing_character_intent():
    graph = asyncio.run(DeterministicPlanner().create_execution_graph(
        "Rig the warrior in the scene.",
        {"characters": [{"id": "char_warrior", "name": "Warrior"}]},
    ))
    assert graph.metadata["intent"] == "CHARACTER_RIGGING"
    assert graph.steps[0].type == OperationType.RIG_CHARACTER
    assert graph.steps[0].parameters["character_id"] == "char_warrior"