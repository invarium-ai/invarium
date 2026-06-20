from __future__ import annotations

import json
from typing import Any

from .base import BaseAdapter
from ..result import AgentResult, ToolCall


class LangGraphAdapter(BaseAdapter):
    """Normalize LangGraph or LangChain agent state into AgentResult."""

    def run(self, agent: Any, prompt: str) -> AgentResult:
        if not hasattr(agent, "invoke"):
            raise TypeError(
                f"LangGraphAdapter expected an invoke-capable graph/agent, got {type(agent).__name__}."
            )
        raw_result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        return self.normalize(prompt, raw_result)

    def normalize(self, prompt: str, raw_result: Any) -> AgentResult:
        messages = self._extract_messages(raw_result)
        tool_calls = self._extract_tool_calls(messages)
        errors = self._extract_errors(raw_result, messages)
        final_output = self._extract_final_output(messages)

        return AgentResult(
            input=prompt,
            final_output=final_output,
            messages=[self._normalize_message(message) for message in messages],
            tool_calls=tool_calls,
            steps=self._count_steps(messages, tool_calls),
            errors=errors,
            metadata={
                "adapter": "langgraph",
                "message_count": len(messages),
                "state_keys": sorted(raw_result.keys()) if isinstance(raw_result, dict) else [],
            },
        )

    def _extract_messages(self, raw_result: Any) -> list[Any]:
        if isinstance(raw_result, dict):
            messages = raw_result.get("messages", [])
            return list(messages) if isinstance(messages, list) else [messages]
        if isinstance(raw_result, list):
            return list(raw_result)
        if hasattr(raw_result, "messages"):
            messages = getattr(raw_result, "messages")
            return list(messages) if isinstance(messages, list) else [messages]
        return []

    def _extract_tool_calls(self, messages: list[Any]) -> list[ToolCall]:
        tool_calls: list[ToolCall] = []
        tool_calls_by_id: dict[str, ToolCall] = {}

        for message in messages:
            for tool_call in self._read_tool_calls(message):
                call_id = self._string_or_none(tool_call.get("id"))
                normalized = ToolCall(
                    name=str(tool_call.get("name", "unknown_tool")),
                    args=tool_call.get("args", {}) if isinstance(tool_call.get("args"), dict) else {},
                    output=None,
                    success=True,
                )
                tool_calls.append(normalized)
                if call_id:
                    tool_calls_by_id[call_id] = normalized

        for message in messages:
            message_type = self._message_type(message)
            if message_type != "tool":
                continue
            tool_call_id = self._string_or_none(self._read_attr(message, "tool_call_id"))
            if tool_call_id and tool_call_id in tool_calls_by_id:
                tool_calls_by_id[tool_call_id].output = self._coerce_output(
                    self._read_attr(message, "content")
                )
                tool_calls_by_id[tool_call_id].success = self._tool_message_succeeded(message)
                continue
            tool_calls.append(
                ToolCall(
                    name=str(self._read_attr(message, "name", default="unknown_tool")),
                    args={},
                    output=self._coerce_output(self._read_attr(message, "content")),
                    success=self._tool_message_succeeded(message),
                )
            )

        return tool_calls

    def _extract_errors(self, raw_result: Any, messages: list[Any]) -> list[str]:
        collected: list[str] = []

        if isinstance(raw_result, dict):
            collected.extend(self._coerce_error_values(raw_result.get("errors")))
            collected.extend(self._coerce_error_values(raw_result.get("error")))

        for message in messages:
            invalid_tool_calls = self._read_attr(message, "invalid_tool_calls", default=[])
            for item in invalid_tool_calls or []:
                text = self._coerce_text(item)
                if text:
                    collected.append(text)

            if self._message_type(message) == "tool" and not self._tool_message_succeeded(message):
                name = self._read_attr(message, "name", default="unknown_tool")
                content = self._coerce_text(self._read_attr(message, "content"))
                status = self._read_attr(message, "status", default="error")
                collected.append(f"Tool `{name}` returned status `{status}`: {content}")

        return collected

    def _extract_final_output(self, messages: list[Any]) -> str:
        for message in reversed(messages):
            message_type = self._message_type(message)
            if message_type in {"ai", "assistant"}:
                return self._coerce_text(self._read_attr(message, "content"))
        if messages:
            return self._coerce_text(self._read_attr(messages[-1], "content"))
        return ""

    def _normalize_message(self, message: Any) -> dict[str, Any]:
        message_type = self._message_type(message)
        return {
            "role": self._message_role(message_type),
            "type": message_type,
            "content": self._coerce_text(self._read_attr(message, "content")),
        }

    def _count_steps(self, messages: list[Any], tool_calls: list[ToolCall]) -> int:
        logical_steps = 0
        for message in messages:
            if self._message_type(message) in {"human", "user", "system"}:
                continue
            logical_steps += 1
        return max(logical_steps, len(tool_calls), 1)

    def _read_tool_calls(self, message: Any) -> list[dict[str, Any]]:
        tool_calls = self._read_attr(message, "tool_calls", default=[])
        if not isinstance(tool_calls, list):
            return []
        return [item for item in tool_calls if isinstance(item, dict)]

    def _message_type(self, message: Any) -> str:
        value = self._read_attr(message, "type", default=None)
        if value is not None:
            return str(value).lower()
        return message.__class__.__name__.replace("Message", "").lower()

    def _message_role(self, message_type: str) -> str:
        if message_type == "human":
            return "user"
        if message_type == "ai":
            return "assistant"
        return message_type

    def _tool_message_succeeded(self, message: Any) -> bool:
        status = str(self._read_attr(message, "status", default="success")).lower()
        return status not in {"error", "failed"}

    def _read_attr(self, source: Any, name: str, *, default: Any = None) -> Any:
        if isinstance(source, dict):
            return source.get(name, default)
        return getattr(source, name, default)

    def _coerce_error_values(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [self._coerce_text(item) for item in value if self._coerce_text(item)]
        text = self._coerce_text(value)
        return [text] if text else []

    def _coerce_output(self, value: Any) -> str | dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return {"items": [self._coerce_text(item) for item in value]}
        return self._coerce_text(value)

    def _coerce_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, dict) and "text" in item:
                    parts.append(self._coerce_text(item["text"]))
                else:
                    parts.append(self._coerce_text(item))
            return "\n".join(part for part in parts if part)
        if isinstance(value, dict):
            try:
                return json.dumps(value, sort_keys=True)
            except TypeError:
                return str(value)
        return str(value)

    def _string_or_none(self, value: Any) -> str | None:
        return str(value) if value is not None else None
