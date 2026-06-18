from __future__ import annotations

import json
from typing import Any

from .base import BaseAdapter
from ..result import AgentResult, ToolCall


class OpenAIAgentsAdapter(BaseAdapter):
    def run(self, agent: Any, prompt: str) -> AgentResult:
        try:
            from agents import Runner
        except ImportError as exc:
            raise ImportError(
                "OpenAI Agents SDK is not installed. Install it with `pip install openai-agents`."
            ) from exc

        run_result = Runner.run_sync(agent, prompt)
        return self.normalize(prompt, run_result)

    def normalize(self, prompt: str, run_result: Any) -> AgentResult:
        items = self._read_items(run_result)
        tool_calls = self._extract_tool_calls(items)
        messages = self._extract_messages(items)
        errors = self._extract_errors(run_result, items)
        final_output = self._coerce_text(self._read_value(run_result, "final_output", default=""))
        usage = self._read_value(run_result, "usage")

        return AgentResult(
            input=prompt,
            final_output=final_output,
            messages=messages,
            tool_calls=tool_calls,
            steps=self._count_steps(items, tool_calls),
            errors=errors,
            metadata={
                "adapter": "openai_agents",
                "item_count": len(items),
                "usage": usage,
            },
        )

    def _read_items(self, run_result: Any) -> list[Any]:
        for name in ("new_items", "items"):
            value = self._read_value(run_result, name)
            if value:
                return list(value)
        return []

    def _extract_tool_calls(self, items: list[Any]) -> list[ToolCall]:
        tool_calls: list[ToolCall] = []
        tool_calls_by_id: dict[str, ToolCall] = {}
        for item in items:
            item_type = str(self._read_value(item, "type", default=item.__class__.__name__)).lower()
            if not self._looks_like_tool_call(item, item_type):
                continue
            call_id = self._tool_call_id(item)
            if item_type == "tool_call_output_item":
                output = self._coerce_output(
                    self._read_value(item, "output", "result", "response", default=None)
                )
                if call_id and call_id in tool_calls_by_id:
                    tool_calls_by_id[call_id].output = output
                    tool_calls_by_id[call_id].success = self._tool_call_succeeded(item)
                    continue
                tool_call = ToolCall(
                    name=self._tool_call_name(item, tool_calls_by_id),
                    args={},
                    output=output,
                    success=self._tool_call_succeeded(item),
                    timestamp=str(self._read_value(item, "timestamp", "created_at", default="")),
                )
                tool_calls.append(tool_call)
                if call_id:
                    tool_calls_by_id[call_id] = tool_call
                continue

            tool_call = ToolCall(
                name=self._tool_call_name(item, tool_calls_by_id),
                args=self._coerce_mapping(
                    self._read_value(
                        item,
                        "arguments",
                        "args",
                        "input",
                        default=self._read_value(self._read_value(item, "raw_item", default={}), "arguments", default={}),
                    )
                ),
                output=self._coerce_output(
                    self._read_value(item, "output", "result", "response", default=None)
                ),
                success=self._tool_call_succeeded(item),
                timestamp=str(self._read_value(item, "timestamp", "created_at", default="")),
            )
            tool_calls.append(tool_call)
            if call_id:
                tool_calls_by_id[call_id] = tool_call
        return tool_calls

    def _extract_messages(self, items: list[Any]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for item in items:
            role = self._read_value(item, "role")
            content = self._read_value(item, "content", "text", default=None)
            item_type = self._read_value(item, "type", default=None)
            if role is None and content is None and item_type is None:
                continue
            messages.append(
                {
                    "role": role,
                    "type": item_type,
                    "content": self._coerce_text(content) if content is not None else "",
                }
            )
        return messages

    def _extract_errors(self, run_result: Any, items: list[Any]) -> list[str]:
        collected: list[str] = []
        for value in self._ensure_list(self._read_value(run_result, "errors", default=[])):
            text = self._coerce_text(value)
            if text:
                collected.append(text)
        for item in items:
            error_value = self._read_value(item, "error", default=None)
            text = self._coerce_text(error_value)
            if text:
                collected.append(text)
        return collected

    def _looks_like_tool_call(self, item: Any, item_type: str) -> bool:
        if "tool" in item_type or "function_call" in item_type:
            return True
        return self._read_value(item, "name", "tool_name", default=None) is not None and (
            self._read_value(item, "arguments", "args", "input", default=None) is not None
        )

    def _count_steps(self, items: list[Any], tool_calls: list[ToolCall]) -> int:
        if not items:
            return max(len(tool_calls), 1)
        logical_steps = 0
        for item in items:
            item_type = str(self._read_value(item, "type", default=item.__class__.__name__)).lower()
            if item_type == "tool_call_output_item":
                continue
            logical_steps += 1
        return max(logical_steps, len(tool_calls), 1)

    def _tool_call_id(self, item: Any) -> str | None:
        raw_item = self._read_value(item, "raw_item", default={})
        value = self._read_value(item, "call_id", "id", default=None)
        if value is None:
            value = self._read_value(raw_item, "call_id", "id", default=None)
        return str(value) if value is not None else None

    def _tool_call_name(self, item: Any, tool_calls_by_id: dict[str, ToolCall]) -> str:
        raw_item = self._read_value(item, "raw_item", default={})
        tool_origin = self._read_value(item, "tool_origin", default=None)
        name = self._read_value(
            item,
            "name",
            "tool_name",
            "call_name",
            default=self._read_value(
                raw_item,
                "name",
                "tool_name",
                "call_name",
                default=self._read_value(tool_origin, "agent_tool_name", default=None),
            ),
        )
        if name is not None:
            return str(name)
        call_id = self._tool_call_id(item)
        if call_id and call_id in tool_calls_by_id:
            return tool_calls_by_id[call_id].name
        return "unknown_tool"

    def _tool_call_succeeded(self, item: Any) -> bool:
        if self._read_value(item, "error", default=None):
            return False
        status = str(self._read_value(item, "status", default="")).lower()
        return status not in {"failed", "error", "cancelled"}

    def _read_value(self, source: Any, *names: str, default: Any = None) -> Any:
        for name in names:
            if isinstance(source, dict) and name in source:
                return source[name]
            if hasattr(source, name):
                return getattr(source, name)
        return default

    def _ensure_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _coerce_mapping(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                loaded = json.loads(value)
            except json.JSONDecodeError:
                return {"raw": value}
            return loaded if isinstance(loaded, dict) else {"value": loaded}
        if value is None:
            return {}
        return {"value": value}

    def _coerce_output(self, value: Any) -> str | dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, (str, dict)):
            return value
        if isinstance(value, list):
            return {"items": value}
        return self._coerce_text(value)

    def _coerce_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return "\n".join(self._coerce_text(item) for item in value if item is not None)
        if isinstance(value, dict):
            try:
                return json.dumps(value, sort_keys=True)
            except TypeError:
                return str(value)
        return str(value)
