"""GameForge AI — Automated Tests for Planner Architecture.
"""
import pytest
from app.planners.base import BasePlanner
from app.planners.deterministic import DeterministicPlanner
from app.planners.llm import LLMPlanner
from app.planners.factory import PlannerFactory
from app.schemas.execution_graph import ExecutionGraph, OperationType, StepStatus
from app.services.validator import ExecutionGraphValidator


@pytest.mark.anyio
async def test_deterministic_planner_cube_prompt():
    planner = DeterministicPlanner()
    graph = await planner.create_execution_graph("Create a large red metallic cube")
    
    is_valid, err = ExecutionGraphValidator.validate(graph)
    assert is_valid, f"Graph failed validation: {err}"
    assert graph.steps[0].type == OperationType.CREATE_CUBE
    assert graph.steps[0].parameters["size"] == 4.0
    assert graph.steps[-1].type == OperationType.EXPORT_GLB


@pytest.mark.anyio
async def test_deterministic_planner_sphere_move():
    planner = DeterministicPlanner()
    graph = await planner.create_execution_graph("Create a blue sphere and move it right 2 meters")
    
    is_valid, err = ExecutionGraphValidator.validate(graph)
    assert is_valid, f"Graph failed validation: {err}"
    assert graph.steps[0].type == OperationType.CREATE_SPHERE
    assert graph.steps[-1].type == OperationType.EXPORT_GLB


def test_planner_factory_fallback():
    planner = PlannerFactory.get_planner(provider="deterministic")
    assert isinstance(planner, DeterministicPlanner)


@pytest.mark.anyio
async def test_llm_planner_fallback_without_key():
    planner = LLMPlanner(provider="gemini", api_key=None)
    graph = await planner.create_execution_graph("Create a sphere")
    
    # Should fall back to DeterministicPlanner seamlessly
    is_valid, err = ExecutionGraphValidator.validate(graph)
    assert is_valid, f"Fallback graph invalid: {err}"
    assert len(graph.steps) >= 2


def test_llm_clean_json_response():
    planner = LLMPlanner(provider="gemini")
    markdown_wrapped = "```json\n{\"id\": \"test\", \"steps\": []}\n```"
    cleaned = planner._clean_json_response(markdown_wrapped)
    assert cleaned == '{"id": "test", "steps": []}'
