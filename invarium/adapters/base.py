from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from invarium.result import AgentResult


class SupportsRun(Protocol):
    def run(self, prompt: str) -> Any:
        ...


@dataclass(slots=True)
class AdapterContext:
    prompt: str
    raw_result: Any


class BaseAdapter:
    """Minimal adapter contract.

    Adapters are responsible for converting framework-specific execution output
    into a normalized AgentResult that assertions can inspect consistently.

    Preferred pattern:
    1. `run(...)` executes the framework-specific agent entry point.
    2. `normalize(...)` converts the raw framework output into AgentResult.
    """

    def run(self, agent: SupportsRun, prompt: str) -> AgentResult:
        raise NotImplementedError

    def normalize(self, prompt: str, raw_result: Any) -> AgentResult:
        raise NotImplementedError
