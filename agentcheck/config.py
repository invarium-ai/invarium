from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CONFIG_FILE = "agentcheck.json"


@dataclass
class AgentCheckConfig:
    runs: int | None = None
    path: str = "."
    fail_on_regression: bool = False
    filter_pattern: str | None = None
    report_dir: str | None = None
    trace_dir: str | None = None

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
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentCheckConfig":
        return cls(
            runs=data.get("runs"),
            path=data.get("path", "."),
            fail_on_regression=bool(data.get("fail_on_regression", False)),
            filter_pattern=data.get("filter"),
            report_dir=data.get("report_dir"),
            trace_dir=data.get("trace_dir"),
        )


def load_config(root: Path | None = None) -> AgentCheckConfig:
    search_root = root or Path.cwd()
    candidate = search_root / CONFIG_FILE
    if not candidate.exists():
        return AgentCheckConfig()
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        return AgentCheckConfig.from_dict(data)
    except Exception:
        return AgentCheckConfig()


def save_config(config: AgentCheckConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")


def _default_config() -> AgentCheckConfig:
    return AgentCheckConfig(
        runs=3,
        path=".",
        fail_on_regression=False,
    )
