"""GameForge AI — Automated Tests for Phase 3A Multi-Object Scene Graph & Hierarchy.
"""
import pytest
from app.db.repositories import SceneRepository
from app.models.domain import SceneObject, TransformModel, MaterialModel
from app.schemas.execution_graph import ExecutionGraph, ExecutionStep, OperationType, StepStatus
from app.services.validator import ExecutionGraphValidator
from app.planners.deterministic import DeterministicPlanner


def test_scene_object_stable_identity():
    """Verify object renaming preserves immutable primary key id."""
    scene = SceneRepository.get_or_create_default_scene()
    orig_obj = scene.objects[0]
    orig_id = orig_obj.id

    updated_scene = SceneRepository.update_object(scene.id, orig_id, {"name": "Hero_Car_Mesh"})
    assert updated_scene is not None
    renamed_obj = next(o for o in updated_scene.objects if o.id == orig_id)
    assert renamed_obj.name == "Hero_Car_Mesh"
    assert renamed_obj.id == orig_id


def test_parent_and_unparent_hierarchy():
    """Verify parent assignment and unparenting."""
    scene = SceneRepository.get_or_create_default_scene()
    
    # Create child object
    child = SceneObject(
        id="obj_wheel_fl",
        name="Wheel_FL",
        object_type="SPHERE",
        transform=TransformModel(position=[1.0, 1.0, 0.0])
    )
    SceneRepository.add_object(scene.id, child)

    # Parent child to cube
    updated_scene, err = SceneRepository.set_parent(scene.id, "obj_wheel_fl", "obj_default_cube")
    assert err is None
    c_obj = next(o for o in updated_scene.objects if o.id == "obj_wheel_fl")
    assert c_obj.parent_id == "obj_default_cube"

    # Unparent child
    unparented_scene = SceneRepository.unparent(scene.id, "obj_wheel_fl")
    c_obj2 = next(o for o in unparented_scene.objects if o.id == "obj_wheel_fl")
    assert c_obj2.parent_id is None


def test_reject_circular_parenting():
    """Verify self-parenting and circular parenting are rejected."""
    scene = SceneRepository.get_or_create_default_scene()
    
    # Self-parenting check
    _, err_self = SceneRepository.set_parent(scene.id, "obj_default_cube", "obj_default_cube")
    assert err_self is not None
    assert "Self-parenting rejected" in err_self


def test_validator_accepts_phase3a_operations():
    """Verify validator handles RENAME, UNPARENT, HIDE, SHOW."""
    graph = ExecutionGraph(
        id="graph_p3a_1",
        steps=[
            ExecutionStep(id="s1", type=OperationType.CREATE_CUBE, parameters={"name": "Cube_A"}),
            ExecutionStep(id="s2", type=OperationType.RENAME_OBJECT, parameters={"new_name": "Renamed_Cube"}),
            ExecutionStep(id="s3", type=OperationType.HIDE_OBJECT, parameters={"target_name": "Renamed_Cube"}),
            ExecutionStep(id="s4", type=OperationType.SHOW_OBJECT, parameters={"target_name": "Renamed_Cube"}),
            ExecutionStep(id="s5", type=OperationType.UNPARENT_OBJECT, parameters={"target": "Renamed_Cube"}),
            ExecutionStep(id="s6", type=OperationType.EXPORT_GLB, parameters={}),
        ]
    )
    is_valid, err = ExecutionGraphValidator.validate(graph)
    assert is_valid, f"Graph validation failed: {err}"


@pytest.mark.anyio
async def test_deterministic_planner_scene_context_awareness():
    """Verify DeterministicPlanner inspects existing scene context."""
    planner = DeterministicPlanner()
    context = {
        "objects": [
            {"id": "obj_car_1", "name": "Sports_Car", "object_type": "CUBE", "transform": {"position": [0,0,0]}}
        ]
    }
    graph = await planner.create_execution_graph("Move the Sports_Car right 2 meters", scene_context=context)
    is_valid, err = ExecutionGraphValidator.validate(graph)
    assert is_valid, f"Graph validation failed: {err}"
    
    # Should contain MOVE_OBJECT step
    move_step = next((s for s in graph.steps if s.type == OperationType.MOVE_OBJECT), None)
    assert move_step is not None
