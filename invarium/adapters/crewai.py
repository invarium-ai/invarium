from __future__ import annotations

import time
from typing import Any

from .base import BaseAdapter
from ..result import AgentResult, ToolCall


class CrewAIAdapter(BaseAdapter):
    """Adapter for CrewAI crews and agents.

    Works with both a full Crew (kickoff) and a single CrewAI Agent
    (execute_task). Pass the crew/agent as the first argument to run().

    Usage with a Crew::

        from crewai import Crew, Agent, Task
        from invarium import agent_test, expect, CrewAIAdapter

        adapter = CrewAIAdapter()

        @agent_test(runs=3)
        def test_my_crew():
            crew = build_my_crew()
            result = adapter.run(crew, "Research AI agents")
            return expect(result).used_any_tool().verify()

    Usage with a single Agent::

        @agent_test(runs=3)
        def test_single_agent():
            agent = build_my_agent()
            result = adapter.run_agent(agent, "Summarize this article")
            return expect(result).finished_successfully().verify()
    """

    def run(self, crew: Any, prompt: str) -> AgentResult:
        try:
            import crewai  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "CrewAI is not installed. Install it with `pip install crewai`."
            ) from exc

        t0 = time.monotonic()
        try:
            raw = crew.kickoff(inputs={"input": prompt, "prompt": prompt, "query": prompt})
            latency = time.monotonic() - t0
        except Exception as exc:
            latency = time.monotonic() - t0
            return AgentResult(
                input=prompt,
                final_output="",
                errors=[str(exc)],
                latency=latency,
                metadata={"adapter": "crewai", "exception_type": type(exc).__name__},
            )
        return self.normalize(prompt, raw, latency=latency)

    def run_agent(self, agent: Any, prompt: str) -> AgentResult:
        try:
            import crewai  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "CrewAI is not installed. Install it with `pip install crewai`."
            ) from exc

        t0 = time.monotonic()
        try:
            from crewai import Task
            task = Task(description=prompt, expected_output="agent response", agent=agent)
            raw = agent.execute_task(task)
            latency = time.monotonic() - t0
        except Exception as exc:
            latency = time.monotonic() - t0
            return AgentResult(
                input=prompt,
                final_output="",
                errors=[str(exc)],
                latency=latency,
                metadata={"adapter": "crewai_agent", "exception_type": type(exc).__name__},
            )
        return self.normalize(prompt, raw, latency=latency)

    def normalize(self, prompt: str, raw: Any, *, latency: float | None = None) -> AgentResult:
        final_output = self._extract_output(raw)
        tool_calls = self._extract_tool_calls(raw)
        errors = self._extract_errors(raw)
        usage = self._read(raw, "token_usage", "usage")

        cost: float | None = None
        if usage:
            cost = self._read(usage, "total_cost", "cost")

        return AgentResult(
            input=prompt,
            final_output=final_output,
            tool_calls=tool_calls,
            steps=max(len(tool_calls), 1),
            errors=errors,
            latency=latency,
            cost=float(cost) if cost is not None else None,
            metadata={"adapter": "crewai", "usage": self._serialize_usage(usage)},
        )

    def _serialize_usage(self, usage: Any) -> Any:
        """Coerce CrewAI usage metrics into a JSON-serializable form.

        Newer CrewAI returns a pydantic ``UsageMetrics`` object for ``token_usage``,
        which is not JSON serializable and would break trace/report writing.
        """
        if usage is None or isinstance(usage, (str, int, float, bool, dict)):
            return usage
        for method in ("model_dump", "dict"):
            if hasattr(usage, method):
                try:
                    return getattr(usage, method)()
                except Exception:  # noqa: BLE001
                    pass
        try:
            return dict(usage)
        except Exception:  # noqa: BLE001
            return str(usage)

    def _extract_output(self, raw: Any) -> str:
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        for key in ("raw", "final_output", "output", "result", "text"):
            val = self._read(raw, key)
            if val and isinstance(val, str):
                return val
        return str(raw)

    def _extract_tool_calls(self, raw: Any) -> list[ToolCall]:
        tasks_output = self._read(raw, "tasks_output", "task_outputs")
        if not tasks_output:
            return []
        calls: list[ToolCall] = []
        for task_out in (tasks_output if isinstance(tasks_output, list) else [tasks_output]):
            tool_name = str(self._read(task_out, "name", "task_name", "description") or "crew_task")
            output = self._read(task_out, "raw", "output", "result")
            calls.append(
                ToolCall(
                    name=tool_name,
                    output=str(output) if output else None,
                    success=not bool(self._read(task_out, "error")),
                )
            )
        return calls

    def _extract_errors(self, raw: Any) -> list[str]:
        err = self._read(raw, "error", "errors")
        if not err:
            return []
        if isinstance(err, list):
            return [str(e) for e in err if e]
        return [str(err)]

    def _read(self, source: Any, *keys: str, default: Any = None) -> Any:
        for key in keys:
            if isinstance(source, dict) and key in source:
                return source[key]
            if hasattr(source, key):
                return getattr(source, key)
        return default
