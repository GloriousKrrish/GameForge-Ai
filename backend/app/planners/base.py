"""GameForge AI — Base Planner Abstraction.

All planners (Deterministic, LLM, OpenAI, Gemini, etc.) must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.execution_graph import ExecutionGraph


class BasePlanner(ABC):
    """Abstract base class for all AI/Deterministic planners."""

    @abstractmethod
    async def create_execution_graph(
        self,
        prompt: str,
        scene_context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionGraph:
        """Translates a natural language prompt (and optional scene context)
        into a validated ExecutionGraph.
        """
        pass
