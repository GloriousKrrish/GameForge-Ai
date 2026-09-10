"""GameForge AI — Security & Execution Boundary Tests.
Verifies that arbitrary code, malformed parameters, and unsupported operations are strictly rejected.
"""
import pytest
from pydantic import ValidationError
from app.schemas.execution_graph import ExecutionGraph, ExecutionStep, OperationType, StepStatus
from app.services.validator import ExecutionGraphValidator


def test_reject_unsupported_operation():
    """Verify Pydantic schema validation rejects non-enum malicious operations."""
    with pytest.raises(ValidationError) as exc_info:
        ExecutionStep(
            id="step_1",
            type="EXECUTE_PYTHON_SCRIPT",  # Malicious attempt
            status=StepStatus.PENDING,
            parameters={"script": "import os; os.system('whoami')"}
        )
    assert "Input should be" in str(exc_info.value)


def test_reject_camera_invalid_fov():
    graph = ExecutionGraph(
        id="graph_sec_2",
        steps=[
            ExecutionStep(
                id="step_1",
                type=OperationType.CREATE_CAMERA,
                status=StepStatus.PENDING,
                parameters={"fov": 999.0}  # Invalid FOV
            ),
            ExecutionStep(id="step_2", type=OperationType.EXPORT_GLB, parameters={})
        ]
    )
    is_valid, err = ExecutionGraphValidator.validate(graph)
    assert not is_valid
    assert "Invalid camera FOV" in err


def test_reject_light_invalid_type():
    graph = ExecutionGraph(
        id="graph_sec_3",
        steps=[
            ExecutionStep(
                id="step_1",
                type=OperationType.CREATE_LIGHT,
                status=StepStatus.PENDING,
                parameters={"light_type": "LASER_BEAM"}  # Invalid light type
            ),
            ExecutionStep(id="step_2", type=OperationType.EXPORT_GLB, parameters={})
        ]
    )
    is_valid, err = ExecutionGraphValidator.validate(graph)
    assert not is_valid
    assert "Invalid light_type" in err
