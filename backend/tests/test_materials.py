"""GameForge AI — Phase 3B Material & Asset System Tests."""
import pytest
from app.models.domain import Material, AlphaMode, SceneObject
from app.db.repositories import MaterialRepository, SceneRepository
from app.schemas.execution_graph import ExecutionGraph, ExecutionStep, OperationType, StepStatus
from app.services.validator import ExecutionGraphValidator
from app.planners.deterministic import DeterministicPlanner


def test_material_schema_defaults_and_validation():
    """Verify Material model creation and default PBR values."""
    mat = Material(id="mat_test_1", name="Test Rubber", base_color=[0.1, 0.1, 0.1], roughness=0.85)
    assert mat.id == "mat_test_1"
    assert mat.name == "Test Rubber"
    assert mat.metallic == 0.4
    assert mat.roughness == 0.85
    assert mat.alpha_mode == AlphaMode.OPAQUE
    assert mat.double_sided is False


def test_material_repository_presets_and_crud():
    """Verify MaterialRepository CRUD operations and preset seeding."""
    materials = MaterialRepository.list_materials()
    assert len(materials) >= 7

    preset_names = [m.name for m in materials]
    assert "Matte Black" in preset_names
    assert "Brushed Gold" in preset_names
    assert "Chrome" in preset_names
    assert "Glass" in preset_names

    created = MaterialRepository.create_material(
        name="Custom Neon",
        base_color=[0.0, 1.0, 0.5],
        emission_color=[0.0, 1.0, 0.5],
        emission_strength=5.0
    )
    assert created.id.startswith("mat_")
    assert created.name == "Custom Neon"

    updated = MaterialRepository.update_material(created.id, {"metallic": 0.8, "opacity": 0.9})
    assert updated is not None
    assert updated.metallic == 0.8
    assert updated.opacity == 0.9

    fetched = MaterialRepository.get_material(created.id)
    assert fetched is not None
    assert fetched.name == "Custom Neon"

    deleted = MaterialRepository.delete_material(created.id)
    assert deleted is True
    assert MaterialRepository.get_material(created.id) is None


def test_material_assignment_and_scene_object_sync():
    """Verify assigning material to scene object and property propagation."""
    scene = SceneRepository.get_or_create_default_scene()
    mat = MaterialRepository.create_material("Emerald", base_color=[0.0, 0.8, 0.3], metallic=0.2, roughness=0.1)

    updated_scene, err = MaterialRepository.assign_material_to_object(scene.id, "obj_default_cube", mat.id)
    assert err is None
    assert updated_scene is not None

    obj = next(o for o in updated_scene.objects if o.id == "obj_default_cube")
    assert obj.material_id == mat.id
    assert obj.material is not None
    assert obj.material.color == "#00CC4C"

    # Property update propagation
    MaterialRepository.update_material(mat.id, {"base_color": [1.0, 0.0, 0.0]})
    reloaded_scene = SceneRepository.get_or_create_default_scene()
    reloaded_obj = next(o for o in reloaded_scene.objects if o.id == "obj_default_cube")
    assert reloaded_obj.material.color == "#FF0000"


def test_validator_accepts_material_operations():
    """Verify ExecutionGraphValidator checks for material operations."""
    graph = ExecutionGraph(
        id="graph_mat_val",
        steps=[
            ExecutionStep(
                id="step_1",
                type=OperationType.CREATE_CUBE,
                parameters={"size": 2.0, "name": "Cube1"}
            ),
            ExecutionStep(
                id="step_2",
                type=OperationType.CREATE_MATERIAL,
                parameters={"name": "Mat_Gold", "base_color": [1.0, 0.84, 0.0], "metallic": 0.9, "roughness": 0.2}
            ),
            ExecutionStep(
                id="step_3",
                type=OperationType.ASSIGN_MATERIAL,
                parameters={"material_name": "Mat_Gold", "target": "Cube1"}
            ),
            ExecutionStep(
                id="step_4",
                type=OperationType.EXPORT_GLB,
                parameters={}
            ),
        ]
    )

    is_valid, err = ExecutionGraphValidator.validate(graph)
    assert is_valid is True
    assert err is None


def test_validator_rejects_invalid_material_parameters():
    """Verify validator bounds check for metallic out of range."""
    graph = ExecutionGraph(
        id="graph_mat_invalid",
        steps=[
            ExecutionStep(
                id="step_1",
                type=OperationType.CREATE_MATERIAL,
                parameters={"name": "Bad_Mat", "metallic": 2.5}
            ),
            ExecutionStep(
                id="step_2",
                type=OperationType.EXPORT_GLB,
                parameters={}
            )
        ]
    )

    is_valid, err = ExecutionGraphValidator.validate(graph)
    assert is_valid is False
    assert "Invalid metallic value" in err


@pytest.mark.anyio
async def test_planner_understands_material_keywords():
    """Verify DeterministicPlanner generates material parameters from prompts."""
    planner = DeterministicPlanner()
    graph = await planner.create_execution_graph("Create a metallic gold cube")

    step_types = [s.type for s in graph.steps]
    assert OperationType.CREATE_CUBE in step_types
    assert OperationType.SET_MATERIAL in step_types

    mat_step = next(s for s in graph.steps if s.type == OperationType.SET_MATERIAL)
    assert mat_step.parameters["metallic"] == 0.9
    assert mat_step.parameters["base_color"] == [1.0, 0.84, 0.0]
