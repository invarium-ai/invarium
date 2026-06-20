from __future__ import annotations

from typing import Any

from .base import BaseAdapter
from ..result import AgentResult, ToolCall


class ExampleAdapter(BaseAdapter):
    """Contributor template for building a new adapter.

    Copy this file when adding support for a new framework and replace the
    placeholder extraction logic with framework-specific behavior.
    """

    def run(self, agent: Any, prompt: str) -> AgentResult:
        raw_result = self._execute_framework_agent(agent, prompt)
        return self.normalize(prompt, raw_result)

    def normalize(self, prompt: str, raw_result: Any) -> AgentResult:
        tool_calls = self._extract_tool_calls(raw_result)
        messages = self._extract_messages(raw_result)
        final_output = self._extract_final_output(raw_result)
        errors = self._extract_errors(raw_result)
        steps = self._count_steps(raw_result, tool_calls)

        return AgentResult(
            input=prompt,
            final_output=final_output,
            messages=messages,
            tool_calls=tool_calls,
            steps=steps,
            errors=errors,
            metadata={
                "adapter": "example",
                "raw_type": type(raw_result).__name__,
            },
        )

    def _execute_framework_agent(self, agent: Any, prompt: str) -> Any:
        raise NotImplementedError("Replace with the framework-specific execution path.")

    def _extract_tool_calls(self, raw_result: Any) -> list[ToolCall]:
        return []

    def _extract_messages(self, raw_result: Any) -> list[dict[str, Any]]:
        return []

    def _extract_final_output(self, raw_result: Any) -> str:
        return ""

    def _extract_errors(self, raw_result: Any) -> list[str]:
        return []

    def _count_steps(self, raw_result: Any, tool_calls: list[ToolCall]) -> int:
        return max(len(tool_calls), 1)
