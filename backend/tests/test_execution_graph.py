"""Tests for Execution Graph schema validation."""
import pytest
from app.schemas.execution_graph import ExecutionGraph, ExecutionStep, OperationType, StepStatus
from app.services.validator import ExecutionGraphValidator


# ---------------------------------------------------------------------------
# Valid graphs
# ---------------------------------------------------------------------------
def test_valid_cube_graph():
    graph = ExecutionGraph(id="g1", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE, parameters={"size": 2.0}),
        ExecutionStep(id="s2", type=OperationType.SET_MATERIAL, parameters={"color": "#FF0000"}),
        ExecutionStep(id="s3", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is True
    assert err is None


def test_valid_sphere_with_transforms():
    graph = ExecutionGraph(id="g2", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_SPHERE, parameters={"radius": 1.5}),
        ExecutionStep(id="s2", type=OperationType.MOVE_OBJECT, parameters={"position": [1, 2, 3]}),
        ExecutionStep(id="s3", type=OperationType.ROTATE_OBJECT, parameters={"rotation": [0, 45, 0]}),
        ExecutionStep(id="s4", type=OperationType.SCALE_OBJECT, parameters={"scale": [2, 2, 2]}),
        ExecutionStep(id="s5", type=OperationType.SET_MATERIAL, parameters={"color": "#00FF00", "metallic": 0.8, "roughness": 0.2}),
        ExecutionStep(id="s6", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is True
    assert err is None


def test_valid_delete_then_create():
    graph = ExecutionGraph(id="g3", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE),
        ExecutionStep(id="s2", type=OperationType.DELETE_OBJECT),
        ExecutionStep(id="s3", type=OperationType.CREATE_SPHERE),
        ExecutionStep(id="s4", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is True


# ---------------------------------------------------------------------------
# Invalid graphs
# ---------------------------------------------------------------------------
def test_empty_graph_fails():
    graph = ExecutionGraph(id="g_empty", steps=[])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "at least one step" in err


def test_missing_export_step_fails():
    graph = ExecutionGraph(id="g_no_export", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "missing required EXPORT_GLB" in err


def test_export_not_last_fails():
    graph = ExecutionGraph(id="g_export_first", steps=[
        ExecutionStep(id="s1", type=OperationType.EXPORT_GLB),
        ExecutionStep(id="s2", type=OperationType.CREATE_CUBE),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "EXPORT_GLB must be the final step" in err


def test_invalid_cube_size_negative():
    graph = ExecutionGraph(id="g_bad_size", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE, parameters={"size": -5.0}),
        ExecutionStep(id="s2", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "Invalid cube size" in err


def test_invalid_cube_size_too_large():
    graph = ExecutionGraph(id="g_huge", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE, parameters={"size": 999}),
        ExecutionStep(id="s2", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "Invalid cube size" in err


def test_invalid_sphere_radius():
    graph = ExecutionGraph(id="g_bad_radius", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_SPHERE, parameters={"radius": -1}),
        ExecutionStep(id="s2", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "Invalid sphere radius" in err


def test_invalid_material_color_type():
    graph = ExecutionGraph(id="g_bad_color", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE),
        ExecutionStep(id="s2", type=OperationType.SET_MATERIAL, parameters={"color": 12345}),
        ExecutionStep(id="s3", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "Invalid color value" in err


def test_invalid_metallic_out_of_range():
    graph = ExecutionGraph(id="g_bad_met", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE),
        ExecutionStep(id="s2", type=OperationType.SET_MATERIAL, parameters={"color": "#FF0000", "metallic": 5.0}),
        ExecutionStep(id="s3", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "Invalid metallic value" in err


def test_invalid_move_position_format():
    graph = ExecutionGraph(id="g_bad_move", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE),
        ExecutionStep(id="s2", type=OperationType.MOVE_OBJECT, parameters={"position": [1, 2]}),
        ExecutionStep(id="s3", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "Invalid position" in err


def test_invalid_rotate_format():
    graph = ExecutionGraph(id="g_bad_rot", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE),
        ExecutionStep(id="s2", type=OperationType.ROTATE_OBJECT, parameters={"rotation": "45deg"}),
        ExecutionStep(id="s3", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "Invalid rotation" in err


def test_invalid_scale_format():
    graph = ExecutionGraph(id="g_bad_scale", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE),
        ExecutionStep(id="s2", type=OperationType.SCALE_OBJECT, parameters={"scale": 2.0}),
        ExecutionStep(id="s3", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "Invalid scale" in err


def test_duplicate_step_ids_fails():
    graph = ExecutionGraph(id="g_dup", steps=[
        ExecutionStep(id="s1", type=OperationType.CREATE_CUBE),
        ExecutionStep(id="s1", type=OperationType.EXPORT_GLB),
    ])
    valid, err = ExecutionGraphValidator.validate(graph)
    assert valid is False
    assert "Duplicate step ID" in err


# ---------------------------------------------------------------------------
# Step status defaults
# ---------------------------------------------------------------------------
def test_step_status_defaults_to_pending():
    step = ExecutionStep(id="test", type=OperationType.CREATE_CUBE)
    assert step.status == StepStatus.PENDING


def test_graph_metadata_field():
    graph = ExecutionGraph(id="g_meta", steps=[
        ExecutionStep(id="s1", type=OperationType.EXPORT_GLB),
    ], metadata={"source": "test"})
    assert graph.metadata["source"] == "test"
