from __future__ import annotations

import os
import time
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
import json

from invarium.result import AgentResult, ToolCall


class HttpAdapter:
    """Run behavioral checks against a deployed agent HTTP endpoint.

    The endpoint is expected to accept a JSON POST body and return a JSON
    response. The mapping layer controls how the request is built and how the
    response is parsed into an AgentResult.

    Minimal usage::

        adapter = HttpAdapter("https://my-agent.example.com/run")
        result = adapter.run_input("Book a table for 2")

    Custom request/response mapping::

        adapter = HttpAdapter(
            url="https://api.example.com/agent",
            request_key="message",
            response_output_key="answer",
            response_tools_key="tool_calls",
            headers={"X-Api-Version": "2"},
            auth_env_var="MY_AGENT_API_KEY",
        )

    Environment-driven endpoint::

        adapter = HttpAdapter.from_env(
            url_env_var="AGENT_ENDPOINT",
            auth_env_var="AGENT_API_KEY",
        )
    """

    def __init__(
        self,
        url: str,
        *,
        request_key: str = "input",
        request_extra: dict[str, Any] | None = None,
        response_output_key: str = "output",
        response_tools_key: str | None = "tool_calls",
        response_steps_key: str | None = "steps",
        response_latency_key: str | None = "latency",
        response_cost_key: str | None = "cost",
        headers: dict[str, str] | None = None,
        auth_env_var: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.url = url
        self.request_key = request_key
        self.request_extra = request_extra or {}
        self.response_output_key = response_output_key
        self.response_tools_key = response_tools_key
        self.response_steps_key = response_steps_key
        self.response_latency_key = response_latency_key
        self.response_cost_key = response_cost_key
        self.timeout = timeout
        self._headers: dict[str, str] = {"Content-Type": "application/json", **(headers or {})}
        if auth_env_var:
            token = os.environ.get(auth_env_var, "")
            if token:
                self._headers["Authorization"] = f"Bearer {token}"

    @classmethod
    def from_env(
        cls,
        *,
        url_env_var: str = "INVARIUM_HTTP_URL",
        auth_env_var: str | None = "INVARIUM_HTTP_TOKEN",
        **kwargs: Any,
    ) -> "HttpAdapter":
        url = os.environ.get(url_env_var, "")
        if not url:
            raise ValueError(
                f"Environment variable `{url_env_var}` is not set. "
                "Set it to your agent endpoint URL."
            )
        return cls(url, auth_env_var=auth_env_var, **kwargs)

    def _build_body(self, input_text: str) -> bytes:
        payload = {self.request_key: input_text, **self.request_extra}
        return json.dumps(payload).encode("utf-8")

    def _parse_tool_calls(self, raw: Any) -> list[ToolCall]:
        if not raw or not isinstance(raw, list):
            return []
        calls: list[ToolCall] = []
        for item in raw:
            if isinstance(item, dict):
                calls.append(
                    ToolCall(
                        name=str(item.get("name", item.get("tool", "unknown"))),
                        args=item.get("args", item.get("arguments", item.get("input", {}))),
                        output=item.get("output", item.get("result")),
                        success=bool(item.get("success", item.get("ok", True))),
                    )
                )
            elif isinstance(item, str):
                calls.append(ToolCall(name=item))
        return calls

    def run_input(self, input_text: str) -> AgentResult:
        body = self._build_body(input_text)
        req = urllib_request.Request(
            self.url,
            data=body,
            headers=self._headers,
            method="POST",
        )
        t0 = time.monotonic()
        try:
            with urllib_request.urlopen(req, timeout=self.timeout) as resp:
                latency = time.monotonic() - t0
                raw_body = resp.read()
        except HTTPError as exc:
            latency = time.monotonic() - t0
            return AgentResult(
                input=input_text,
                final_output="",
                errors=[f"HTTP {exc.code}: {exc.reason}"],
                latency=latency,
            )
        except URLError as exc:
            latency = time.monotonic() - t0
            return AgentResult(
                input=input_text,
                final_output="",
                errors=[f"Connection error: {exc.reason}"],
                latency=latency,
            )

        try:
            data = json.loads(raw_body)
        except Exception as exc:
            return AgentResult(
                input=input_text,
                final_output="",
                errors=[f"JSON parse error: {exc}"],
                latency=latency,
            )

        final_output = str(data.get(self.response_output_key, ""))
        tool_calls = self._parse_tool_calls(
            data.get(self.response_tools_key) if self.response_tools_key else None
        )
        steps = int(data.get(self.response_steps_key, len(tool_calls))) if self.response_steps_key else len(tool_calls)
        reported_latency = float(data.get(self.response_latency_key, latency)) if self.response_latency_key else latency
        cost = float(data[self.response_cost_key]) if self.response_cost_key and self.response_cost_key in data else None

        return AgentResult(
            input=input_text,
            final_output=final_output,
            tool_calls=tool_calls,
            steps=steps,
            latency=reported_latency,
            cost=cost,
            metadata={"http_url": self.url},
        )
