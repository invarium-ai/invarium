from __future__ import annotations

from typing import Any

from .base import BaseAdapter, SupportsRun
from ..result import AgentResult


class PythonAdapter(BaseAdapter):
    def run(self, agent: SupportsRun, prompt: str) -> AgentResult:
        result = agent.run(prompt)
        if isinstance(result, AgentResult):
            return result
        if isinstance(result, dict):
            return AgentResult.from_dict(result)
        raise TypeError(f"Unsupported plain Python agent return type: {type(result).__name__}")
