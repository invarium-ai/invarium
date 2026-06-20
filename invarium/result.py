from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ToolCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    output: str | dict[str, Any] | None = None
    success: bool = True
    timestamp: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentResult:
    input: str
    final_output: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    steps: int = 0
    errors: list[str] = field(default_factory=list)
    latency: float | None = None
    cost: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tool_calls"] = [tool.to_dict() for tool in self.tool_calls]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentResult":
        tool_calls = [ToolCall(**tool) for tool in data.get("tool_calls", [])]
        return cls(
            input=data.get("input", ""),
            final_output=data.get("final_output", ""),
            messages=data.get("messages", []),
            tool_calls=tool_calls,
            steps=data.get("steps", 0),
            errors=data.get("errors", []),
            latency=data.get("latency"),
            cost=data.get("cost"),
            metadata=data.get("metadata", {}),
        )
