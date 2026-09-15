"""GameForge AI — Phase 6A Animation Foundation & Contract Test Suite.

Empirically verifies animation domain models, SQLite persistence, timing bounds validation,
character & rig relationship integrity, project isolation, API endpoints, and Execution Graph contract validation.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.domain import (
    AnimationCreateRequest, AnimationStatus, AnimationType, AnimationUpdateRequest,
    AssetModel, AssetSourceType, AssetStatus, CharacterStatus, CharacterType,
    RigCharacterRequest, RigType,
)
from app.schemas.execution_graph import ExecutionGraph, ExecutionStep, OperationType
from app.services.animation_manager import AnimationValidationError, animation_manager
from app.services.asset_manager import asset_manager
from app.services.character_manager import character_manager
from app.services.validator import ExecutionGraphValidator

client = TestClient(app)


def make_test_asset(asset_id="asset_anim_test_1", project_id="proj_default"):
    return asset_manager.save_asset(AssetModel(
        id=asset_id,
        project_id=project_id,
        name="Anim Test Asset",
        source_type=AssetSourceType.GENERATED,
        status=AssetStatus.READY,
        glb_url="/exports/test_anim.glb",
    ))


def make_test_character(asset, name="Anim Hero"):
    return character_manager.create_character(asset, name, CharacterType.HUMANOID)


def test_animation_creation_and_persistence():
    asset = make_test_asset("asset_anim_1")
    char = make_test_character(asset, "Warrior 1")
    
    req = AnimationCreateRequest(
        character_id=char.id,
        name="Warrior Walk",
        animation_type=AnimationType.WALK,
        duration_seconds=2.5,
        fps=30,
        frame_start=1,
        frame_end=75,
        is_looping=True,
    )
    anim = animation_manager.create_animation(char, req)

    assert anim.id.startswith("anim_")
    assert anim.character_id == char.id
    assert anim.project_id == char.project_id
    assert anim.name == "Warrior Walk"
    assert anim.animation_type == AnimationType.WALK
    assert anim.status == AnimationStatus.PENDING
    assert anim.duration_seconds == 2.5
    assert anim.fps == 30
    assert anim.frame_start == 1
    assert anim.frame_end == 75

    # Verify retrieval from persistence
    loaded = animation_manager.get_animation(anim.id)
    assert loaded is not None
    assert loaded.id == anim.id
    assert loaded.name == anim.name

    # Verify list filtering
    anims = animation_manager.list_animations(character_id=char.id)
    assert len(anims) >= 1
    assert anims[0].id == anim.id


def test_backend_restart_persistence():
    asset = make_test_asset("asset_anim_persistence")
    char = make_test_character(asset, "Persistent Character")
    req = AnimationCreateRequest(
        character_id=char.id,
        name="Persistent Jump",
        animation_type=AnimationType.JUMP,
        duration_seconds=1.2,
        fps=60,
    )
    anim = animation_manager.create_animation(char, req)

    # Re-query to simulate backend restart
    from app.db.database import db
    with db.get_connection() as conn:
        row = conn.execute("SELECT data_json FROM animations WHERE id = ?", (anim.id,)).fetchone()
        assert row is not None

    reloaded = animation_manager.get_animation(anim.id)
    assert reloaded is not None
    assert reloaded.name == "Persistent Jump"
    assert reloaded.fps == 60


def test_animation_timing_bounds_validation():
    asset = make_test_asset("asset_anim_timing")
    char = make_test_character(asset, "Timing Character")

    # Invalid negative duration
    with pytest.raises(AnimationValidationError, match="duration_seconds"):
        animation_manager.create_animation(char, AnimationCreateRequest(
            character_id=char.id, name="Invalid Duration", duration_seconds=-1.0
        ))

    # Invalid FPS (0)
    with pytest.raises(AnimationValidationError, match="fps"):
        animation_manager.create_animation(char, AnimationCreateRequest(
            character_id=char.id, name="Invalid FPS", fps=0
        ))

    # Invalid frame range (frame_end < frame_start)
    with pytest.raises(AnimationValidationError, match="frame_end"):
        animation_manager.create_animation(char, AnimationCreateRequest(
            character_id=char.id, name="Invalid Range", frame_start=100, frame_end=10
        ))


def test_character_and_rig_relationship_validation():
    asset = make_test_asset("asset_anim_rel")
    char_a = make_test_character(asset, "Char A")

    asset_b = make_test_asset("asset_anim_rel_b")
    char_b = make_test_character(asset_b, "Char B")
    _, rig_b, _ = character_manager.rig_character(char_b, RigCharacterRequest())

    # Try assigning rig_b to char_a animation -> should raise validation error
    with pytest.raises(AnimationValidationError, match="unlinked|invalid"):
        animation_manager.create_animation(char_a, AnimationCreateRequest(
            character_id=char_a.id, name="Mismatched Rig", rig_id=rig_b.id
        ))


def test_project_isolation_rejection():
    asset_a = make_test_asset("asset_proj_a", project_id="proj_a")
    char_a = character_manager.create_character(asset_a, "Scoped A", CharacterType.HUMANOID)

    with pytest.raises(AnimationValidationError, match="Project mismatch"):
        animation_manager.create_animation(char_a, AnimationCreateRequest(
            character_id=char_a.id, name="Cross Project", project_id="proj_b"
        ))


def test_execution_graph_animation_operations():
    graph = ExecutionGraph(id="anim_graph_1", steps=[
        ExecutionStep(
            id="create_anim",
            type=OperationType.CREATE_ANIMATION,
            parameters={"character_id": "char_123", "name": "Run Cycle", "animation_type": "RUN", "duration_seconds": 2.0, "fps": 30}
        ),
        ExecutionStep(
            id="val_anim",
            type=OperationType.VALIDATE_ANIMATION,
            parameters={"animation_id": "anim_123"}
        ),
        ExecutionStep(
            id="export",
            type=OperationType.EXPORT_GLB,
            parameters={}
        ),
    ])
    valid, error = ExecutionGraphValidator.validate(graph)
    assert valid, error

    # Invalid animation operation parameters
    invalid_graph = graph.model_copy(deep=True)
    invalid_graph.steps[0].parameters["fps"] = 999  # > 120
    valid, error = ExecutionGraphValidator.validate(invalid_graph)
    assert not valid
    assert "fps" in error


def test_animation_api_endpoints():
    asset = make_test_asset("asset_api_anim")
    char = make_test_character(asset, "API Character")

    # POST create animation
    res = client.post(f"/api/v1/characters/{char.id}/animations", json={
        "character_id": char.id,
        "name": "API Wave",
        "animation_type": "WAVE",
        "duration_seconds": 1.5,
        "fps": 30,
    })
    assert res.status_code == 201
    data = res.json()
    anim_id = data["id"]
    assert data["name"] == "API Wave"
    assert data["character_id"] == char.id

    # GET list character animations
    res_list = client.get(f"/api/v1/characters/{char.id}/animations")
    assert res_list.status_code == 200
    anims = res_list.json()
    assert len(anims) >= 1
    assert anims[0]["id"] == anim_id

    # GET animation details
    res_get = client.get(f"/api/v1/animations/{anim_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == anim_id

    # PATCH update animation
    res_patch = client.patch(f"/api/v1/animations/{anim_id}", json={
        "name": "API Wave Updated",
        "duration_seconds": 3.0,
    })
    assert res_patch.status_code == 200
    assert res_patch.json()["name"] == "API Wave Updated"
    assert res_patch.json()["duration_seconds"] == 3.0

    # DELETE animation
    res_del = client.delete(f"/api/v1/animations/{anim_id}")
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

    # Confirm 404 after deletion
    res_get_deleted = client.get(f"/api/v1/animations/{anim_id}")
    assert res_get_deleted.status_code == 404
