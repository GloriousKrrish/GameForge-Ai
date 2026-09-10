"""GameForge AI — LLM Structured Planner.

Uses LLM APIs (Gemini, OpenAI, Anthropic, or custom local server) to convert
natural language prompts into validated ExecutionGraph JSON structures.

STRICT SECURITY RULE:
The LLM returns raw structured JSON ONLY. It NEVER executes arbitrary code
or system calls directly. All output MUST pass through ExecutionGraphValidator.
"""
import json
import logging
import os
import uuid
from typing import Dict, Any, Optional
import httpx

from app.planners.base import BasePlanner
from app.planners.deterministic import DeterministicPlanner
from app.schemas.execution_graph import ExecutionGraph, OperationType
from app.services.validator import ExecutionGraphValidator

logger = logging.getLogger("gameforge.planner.llm")

SYSTEM_PROMPT = """You are the AI Planner for GameForge AI, a 3D creation system.
Your job is to translate natural-language user prompts into a structured 3D ExecutionGraph JSON.

ALLOWED OPERATION TYPES:
- CREATE_CUBE: parameters {"size": float, "location": [x,y,z], "name": string}
- CREATE_SPHERE: parameters {"radius": float, "location": [x,y,z], "name": string}
- CREATE_CAMERA: parameters {"location": [x,y,z], "rotation": [deg_x,deg_y,deg_z], "fov": float, "name": string}
- CREATE_LIGHT: parameters {"light_type": "POINT"|"SUN"|"SPOT"|"AREA", "energy": float, "location": [x,y,z], "name": string}
- DELETE_OBJECT: parameters {"target_name": string}
- MOVE_OBJECT: parameters {"position": [x,y,z]}
- ROTATE_OBJECT: parameters {"rotation": [deg_x,deg_y,deg_z]}
- SCALE_OBJECT: parameters {"scale": [x,y,z]}
- SET_MATERIAL: parameters {"color": "#HEX", "metallic": float(0-1), "roughness": float(0-1)}
- DUPLICATE_OBJECT: parameters {"offset": [x,y,z]}
- PARENT_OBJECT: parameters {"parent": string}
- EXPORT_GLB: parameters {} (MUST BE THE FINAL STEP)

CRITICAL RULES:
1. Return ONLY valid JSON matching the ExecutionGraph structure. Do not output markdown, code blocks, or explanatory text.
2. The final step MUST ALWAYS be EXPORT_GLB.
3. Keep step IDs unique, e.g., "step_1", "step_2".
4. Never generate arbitrary code or Python scripts.

Output format example:
{
  "id": "graph_123",
  "version": "1.0",
  "steps": [
    {
      "id": "step_1",
      "type": "CREATE_CUBE",
      "status": "PENDING",
      "parameters": {"size": 2.0, "location": [0,0,0], "name": "Red_Cube"}
    },
    {
      "id": "step_2",
      "type": "SET_MATERIAL",
      "status": "PENDING",
      "parameters": {"color": "#FF0000", "metallic": 0.8, "roughness": 0.2}
    },
    {
      "id": "step_3",
      "type": "MOVE_OBJECT",
      "status": "PENDING",
      "parameters": {"position": [2.0, 0.0, 0.0]}
    },
    {
      "id": "step_4",
      "type": "EXPORT_GLB",
      "status": "PENDING",
      "parameters": {}
    }
  ]
}
"""


class LLMPlanner(BasePlanner):
    """Provider-agnostic LLM Planner with strict JSON validation & fallback."""

    def __init__(
        self,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = provider.lower()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        self.api_url = api_url or os.environ.get("LLM_API_URL")
        self.model = model or os.environ.get("LLM_MODEL_NAME") or "gemini-2.5-flash"
        self.fallback_planner = DeterministicPlanner()

    async def create_execution_graph(
        self,
        prompt: str,
        scene_context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionGraph:
        if not self.api_key and not self.api_url:
            logger.info("No API key configured for LLMPlanner. Falling back to DeterministicPlanner.")
            return await self.fallback_planner.create_execution_graph(prompt, scene_context)

        try:
            raw_json_str = await self._call_llm_api(prompt, scene_context)
            if not raw_json_str:
                logger.warning("Empty response from LLM provider. Using fallback planner.")
                return await self.fallback_planner.create_execution_graph(prompt, scene_context)

            # Strip markdown fence blocks if present
            cleaned_json = self._clean_json_response(raw_json_str)
            graph_dict = json.loads(cleaned_json)
            
            # Populate defaults if omitted by LLM
            if "id" not in graph_dict:
                graph_dict["id"] = f"graph_llm_{uuid.uuid4().hex[:8]}"
            if "version" not in graph_dict:
                graph_dict["version"] = "1.0"
            if "metadata" not in graph_dict:
                graph_dict["metadata"] = {}
            graph_dict["metadata"]["planner"] = f"llm_{self.provider}"
            graph_dict["metadata"]["prompt"] = prompt

            graph = ExecutionGraph.model_validate(graph_dict)

            # Validate against strict GameForge validator
            is_valid, err_msg = ExecutionGraphValidator.validate(graph)
            if not is_valid:
                logger.error("LLM generated invalid graph: %s. Using fallback planner.", err_msg)
                return await self.fallback_planner.create_execution_graph(prompt, scene_context)

            logger.info("LLMPlanner generated valid ExecutionGraph with %d steps.", len(graph.steps))
            return graph

        except Exception as e:
            logger.error("LLMPlanner error (%s): %s. Falling back to DeterministicPlanner.", type(e).__name__, e)
            return await self.fallback_planner.create_execution_graph(prompt, scene_context)

    async def _call_llm_api(self, prompt: str, scene_context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        user_message = f"User Request: {prompt}"
        if scene_context:
            user_message += f"\nActive Scene Context: {json.dumps(scene_context)}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            if self.provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\n{user_message}"}]}],
                    "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
                }
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]

            elif self.provider in ("openai", "custom"):
                endpoint = self.api_url or "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": self.model or "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                }
                resp = await client.post(endpoint, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]

            else:
                logger.warning("Unsupported LLM provider: %s", self.provider)
                return None

    def _clean_json_response(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text
