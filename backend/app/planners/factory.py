"""GameForge AI — Planner Factory.

Instantiates configured Planner based on environment configuration.
"""
import os
from typing import Optional
from app.planners.base import BasePlanner
from app.planners.deterministic import DeterministicPlanner
from app.planners.llm import LLMPlanner


class PlannerFactory:
    """Factory for obtaining the active Planner strategy."""

    @staticmethod
    def get_planner(
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> BasePlanner:
        """Returns the appropriate Planner based on env vars or explicit arguments."""
        env_provider = provider or os.environ.get("GAMEFORGE_PLANNER_PROVIDER", "deterministic").lower()

        if env_provider in ("gemini", "openai", "anthropic", "llm"):
            return LLMPlanner(provider=env_provider, api_key=api_key)
        else:
            return DeterministicPlanner()
