from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


CONFIG_FILE = "invarium.json"

AdapterType = Literal["python", "openai_agents", "langgraph", "crewai", "http"]

_HTTP_FIELDS = {
    "url", "request_key", "request_extra", "response_output_key",
    "response_tools_key", "response_steps_key", "response_latency_key",
    "response_cost_key", "auth_env_var", "timeout",
}


@dataclass
class AdapterConfig:
    """Adapter selection and options stored in invarium.json.

    For code-based adapters (python, openai_agents, langgraph, crewai) only
    ``type`` is relevant — the agent object itself must be provided in test code.
    For the ``http`` adapter all fields map directly to HttpAdapter.__init__.
    """

    type: AdapterType = "python"
    # HTTP adapter options
    url: str | None = None
    request_key: str = "input"
    request_extra: dict[str, Any] = field(default_factory=dict)
    response_output_key: str = "output"
    response_tools_key: str | None = "tool_calls"
    response_steps_key: str | None = "steps"
    response_latency_key: str | None = "latency"
    response_cost_key: str | None = "cost"
    auth_env_var: str | None = None
    timeout: float = 30.0

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": self.type}
        if self.type == "http":
            if self.url is not None:
                out["url"] = self.url
            out["request_key"] = self.request_key
            if self.request_extra:
                out["request_extra"] = self.request_extra
            out["response_output_key"] = self.response_output_key
            if self.response_tools_key is not None:
                out["response_tools_key"] = self.response_tools_key
            if self.response_steps_key is not None:
                out["response_steps_key"] = self.response_steps_key
            if self.response_latency_key is not None:
                out["response_latency_key"] = self.response_latency_key
            if self.response_cost_key is not None:
                out["response_cost_key"] = self.response_cost_key
            if self.auth_env_var is not None:
                out["auth_env_var"] = self.auth_env_var
            out["timeout"] = self.timeout
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdapterConfig":
        adapter_type = data.get("type", "python")
        return cls(
            type=adapter_type,
            url=data.get("url"),
            request_key=data.get("request_key", "input"),
            request_extra=data.get("request_extra", {}),
            response_output_key=data.get("response_output_key", "output"),
            response_tools_key=data.get("response_tools_key", "tool_calls"),
            response_steps_key=data.get("response_steps_key", "steps"),
            response_latency_key=data.get("response_latency_key", "latency"),
            response_cost_key=data.get("response_cost_key", "cost"),
            auth_env_var=data.get("auth_env_var"),
            timeout=float(data.get("timeout", 30.0)),
        )

    def build(self) -> Any:
        """Instantiate and return the adapter described by this config.

        For HTTP adapters all options are applied. For code-based adapters
        the corresponding adapter class is returned with no arguments — the
        caller still needs to supply the agent object at run time.
        """
        if self.type == "http":
            from invarium.adapters.http import HttpAdapter
            if not self.url:
                raise ValueError(
                    "adapter.url is required when adapter.type is 'http'. "
                    "Set it in invarium.json or use HttpAdapter.from_env()."
                )
            return HttpAdapter(
                self.url,
                request_key=self.request_key,
                request_extra=self.request_extra or None,
                response_output_key=self.response_output_key,
                response_tools_key=self.response_tools_key,
                response_steps_key=self.response_steps_key,
                response_latency_key=self.response_latency_key,
                response_cost_key=self.response_cost_key,
                auth_env_var=self.auth_env_var,
                timeout=self.timeout,
            )
        if self.type == "openai_agents":
            from invarium.adapters.openai_agents import OpenAIAgentsAdapter
            return OpenAIAgentsAdapter()
        if self.type == "langgraph":
            from invarium.adapters.langgraph import LangGraphAdapter
            return LangGraphAdapter()
        if self.type == "crewai":
            from invarium.adapters.crewai import CrewAIAdapter
            return CrewAIAdapter()
        from invarium.adapters.python import PythonAdapter
        return PythonAdapter()


@dataclass
class InvariumConfig:
    runs: int | None = None
    path: str = "."
    fail_on_regression: bool = False
    filter_pattern: str | None = None
    report_dir: str | None = None
    trace_dir: str | None = None
    adapter: AdapterConfig | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"path": self.path, "fail_on_regression": self.fail_on_regression}
        if self.runs is not None:
            out["runs"] = self.runs
        if self.filter_pattern is not None:
            out["filter"] = self.filter_pattern
        if self.report_dir is not None:
            out["report_dir"] = self.report_dir
        if self.trace_dir is not None:
            out["trace_dir"] = self.trace_dir
        if self.adapter is not None:
            out["adapter"] = self.adapter.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InvariumConfig":
        adapter: AdapterConfig | None = None
        if "adapter" in data and isinstance(data["adapter"], dict):
            adapter = AdapterConfig.from_dict(data["adapter"])
        return cls(
            runs=data.get("runs"),
            path=data.get("path", "."),
            fail_on_regression=bool(data.get("fail_on_regression", False)),
            filter_pattern=data.get("filter"),
            report_dir=data.get("report_dir"),
            trace_dir=data.get("trace_dir"),
            adapter=adapter,
        )


def load_config(root: Path | None = None) -> InvariumConfig:
    search_root = root or Path.cwd()
    candidate = search_root / CONFIG_FILE
    if not candidate.exists():
        return InvariumConfig()
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        return InvariumConfig.from_dict(data)
    except Exception:
        return InvariumConfig()


def save_config(config: InvariumConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")


def _default_config() -> InvariumConfig:
    return InvariumConfig(
        runs=3,
        path=".",
        fail_on_regression=False,
        adapter=AdapterConfig(type="python"),
    )
