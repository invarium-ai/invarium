from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ARTIFACT_ROOT = Path(".invarium")
TRACE_DIR = ARTIFACT_ROOT / "traces"
BASELINE_DIR = ARTIFACT_ROOT / "baselines"
REPORT_DIR = ARTIFACT_ROOT / "reports"


def ensure_artifact_dirs() -> None:
    for path in (ARTIFACT_ROOT, TRACE_DIR, BASELINE_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
