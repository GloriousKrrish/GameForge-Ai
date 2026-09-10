"""Tests for the deterministic prompt interpreter (job_manager.default_graph_for_prompt)."""
from app.services.job_manager import default_graph_for_prompt
from app.schemas.execution_graph import OperationType


def test_cube_prompt():
    graph = default_graph_for_prompt("create a cube")
    op_types = [s.type for s in graph.steps]
    assert OperationType.CREATE_CUBE in op_types
    assert OperationType.SET_MATERIAL in op_types
    assert graph.steps[-1].type == OperationType.EXPORT_GLB


def test_sphere_prompt():
    graph = default_graph_for_prompt("create a blue sphere")
    op_types = [s.type for s in graph.steps]
    assert OperationType.CREATE_SPHERE in op_types
    assert OperationType.SET_MATERIAL in op_types
    # Check color was parsed
    mat_step = next(s for s in graph.steps if s.type == OperationType.SET_MATERIAL)
    assert mat_step.parameters["color"] == "#0000FF"


def test_metallic_keyword():
    graph = default_graph_for_prompt("create a metallic red cube")
    mat_step = next(s for s in graph.steps if s.type == OperationType.SET_MATERIAL)
    assert mat_step.parameters["metallic"] == 0.8
    assert mat_step.parameters["color"] == "#FF0000"


def test_shiny_keyword():
    graph = default_graph_for_prompt("create a shiny green sphere")
    mat_step = next(s for s in graph.steps if s.type == OperationType.SET_MATERIAL)
    assert mat_step.parameters["roughness"] == 0.2


def test_move_keyword_adds_step():
    graph = default_graph_for_prompt("create a cube and move it")
    op_types = [s.type for s in graph.steps]
    assert OperationType.MOVE_OBJECT in op_types


def test_rotate_keyword_adds_step():
    graph = default_graph_for_prompt("create a rotated sphere")
    op_types = [s.type for s in graph.steps]
    assert OperationType.ROTATE_OBJECT in op_types


def test_scale_keyword_adds_step():
    graph = default_graph_for_prompt("create a scaled cube")
    op_types = [s.type for s in graph.steps]
    assert OperationType.SCALE_OBJECT in op_types


def test_large_keyword():
    graph = default_graph_for_prompt("create a large red cube")
    create_step = next(s for s in graph.steps if s.type == OperationType.CREATE_CUBE)
    assert create_step.parameters["size"] == 3.0


def test_small_keyword():
    graph = default_graph_for_prompt("create a tiny sphere")
    create_step = next(s for s in graph.steps if s.type == OperationType.CREATE_SPHERE)
    assert create_step.parameters["radius"] == 0.5


def test_export_is_always_last():
    graph = default_graph_for_prompt("create a big rotated metallic gold sphere and move and scale it")
    assert graph.steps[-1].type == OperationType.EXPORT_GLB
    # Should have: CREATE_SPHERE, SET_MATERIAL, MOVE, ROTATE, SCALE, EXPORT
    assert len(graph.steps) >= 5
