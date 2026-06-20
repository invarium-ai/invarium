from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .storage import ARTIFACT_ROOT


HISTORY_FILE = ARTIFACT_ROOT / "history.json"
HISTORY_LIMIT = 200


@dataclass
class HistoryEntry:
    run_id: str
    created_at: str
    suite_id: str | None
    total_tests: int
    passed_tests: int
    failed_tests: int
    has_regression: bool
    filter_pattern: str | None = None
    tests: list[dict] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if not self.total_tests:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(
            run_id=data.get("run_id", ""),
            created_at=data.get("created_at", ""),
            suite_id=data.get("suite_id"),
            total_tests=data.get("total_tests", 0),
            passed_tests=data.get("passed_tests", 0),
            failed_tests=data.get("failed_tests", 0),
            has_regression=data.get("has_regression", False),
            filter_pattern=data.get("filter_pattern"),
            tests=data.get("tests", []),
        )


def _load_history() -> list[HistoryEntry]:
    if not HISTORY_FILE.exists():
        return []
    try:
        raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return [HistoryEntry.from_dict(e) for e in raw if isinstance(e, dict)]
    except Exception:
        return []


def _save_history(entries: list[HistoryEntry]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps([e.to_dict() for e in entries], indent=2),
        encoding="utf-8",
    )


def record_run(
    reports: list[dict],
    suite_id: str | None,
    has_regression: bool,
    *,
    filter_pattern: str | None = None,
) -> HistoryEntry:
    passed = sum(1 for r in reports if not r.get("failed_runs", 0))
    entry = HistoryEntry(
        run_id=uuid4().hex[:12],
        created_at=datetime.now(timezone.utc).isoformat(),
        suite_id=suite_id,
        total_tests=len(reports),
        passed_tests=passed,
        failed_tests=len(reports) - passed,
        has_regression=has_regression,
        filter_pattern=filter_pattern,
        tests=[
            {
                "name": r["test_name"],
                "success_rate": r.get("success_rate", 0),
                "failed_runs": r.get("failed_runs", 0),
                "average_steps": r.get("average_steps", 0),
                "flakiness_score": r.get("flakiness_score", 0),
            }
            for r in reports
        ],
    )
    history = _load_history()
    history.append(entry)
    if len(history) > HISTORY_LIMIT:
        history = history[-HISTORY_LIMIT:]
    _save_history(history)
    return entry


def get_history(limit: int = 20) -> list[HistoryEntry]:
    all_entries = _load_history()
    return list(reversed(all_entries))[:limit]


def get_entry(run_id: str) -> HistoryEntry | None:
    for entry in _load_history():
        if entry.run_id == run_id or entry.run_id.startswith(run_id):
            return entry
    return None
