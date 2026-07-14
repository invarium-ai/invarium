from __future__ import annotations

import asyncio
import inspect

from .base import BaseAdapter, SupportsRun
from ..result import AgentResult


class PythonAdapter(BaseAdapter):
    def run(self, agent: SupportsRun, prompt: str) -> AgentResult:
        result = agent.run(prompt)

        if inspect.isawaitable(result):
            result = asyncio.run(result)

        if isinstance(result, AgentResult):
            return result

        if isinstance(result, dict):
            return AgentResult.from_dict(result)

        raise TypeError(
            f"Unsupported plain Python agent return type: {type(result).__name__}"
        )