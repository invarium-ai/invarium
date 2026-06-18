from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .assertions import AssertionRecord
from .result import AgentResult


@dataclass(slots=True)
class TestRun:
    test_name: str
    run_id: str
    result: AgentResult
    assertions: list[AssertionRecord] = field(default_factory=list)
    passed: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_name": self.test_name,
            "run_id": self.run_id,
            "result": self.result.to_dict(),
            "assertions": [asdict(item) for item in self.assertions],
            "passed": self.passed,
            "error": self.error,
        }


@dataclass(slots=True)
class TestReport:
    test_name: str
    total_runs: int
    passed_runs: int
    failed_runs: int
    success_rate: float
    failure_reasons: list[str]
    average_steps: float
    tool_presence: dict[str, float] = field(default_factory=dict)
    common_tool_paths: list[dict[str, Any]] = field(default_factory=list)
    regression: bool | None = None
    failure_categories: dict[str, int] = field(default_factory=dict)
    flakiness_score: float = 0.0
    unstable_tool_paths: bool = False
    average_latency: float | None = None
    average_cost: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SessionReport:
    created_at: str
    reports: list[TestReport]
    suite_id: str | None = None
    baseline_comparison: dict[str, Any] = field(default_factory=dict)
    trace_file: str | None = None
    markdown_report_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "reports": [report.to_dict() for report in self.reports],
            "suite_id": self.suite_id,
            "baseline_comparison": self.baseline_comparison,
            "trace_file": self.trace_file,
            "markdown_report_file": self.markdown_report_file,
        }


def new_run_id() -> str:
    return uuid4().hex


def _build_tool_presence(runs: list[TestRun]) -> dict[str, float]:
    total_runs = len(runs)
    if not total_runs:
        return {}

    tool_counts = Counter()
    for run in runs:
        for tool_name in {tool.name for tool in run.result.tool_calls}:
            tool_counts[tool_name] += 1
    return {
        tool_name: (count / total_runs) * 100
        for tool_name, count in sorted(tool_counts.items())
    }


def _build_common_tool_paths(runs: list[TestRun], *, limit: int = 3) -> list[dict[str, Any]]:
    total_runs = len(runs)
    if not total_runs:
        return []

    path_counts = Counter(
        tuple(tool.name for tool in run.result.tool_calls)
        for run in runs
        if run.result.tool_calls
    )
    common_paths: list[dict[str, Any]] = []
    for path, count in path_counts.most_common(limit):
        common_paths.append(
            {
                "path": list(path),
                "count": count,
                "rate": (count / total_runs) * 100,
            }
        )
    return common_paths


def _build_failure_categories(runs: list[TestRun]) -> dict[str, int]:
    cats: Counter = Counter()
    for run in runs:
        if run.error and not run.assertions:
            cats["runtime_error"] += 1
        for assertion in run.assertions:
            if not assertion.passed and assertion.category:
                cats[assertion.category] += 1
    return dict(cats.most_common())


def _compute_flakiness_score(runs: list[TestRun]) -> float:
    if len(runs) < 2:
        return 0.0
    outcomes = [1.0 if run.passed else 0.0 for run in runs]
    mean = sum(outcomes) / len(outcomes)
    if mean == 0.0 or mean == 1.0:
        return 0.0
    variance = sum((x - mean) ** 2 for x in outcomes) / len(outcomes)
    return round(min(variance * 4, 1.0), 3)


def _has_unstable_tool_paths(runs: list[TestRun]) -> bool:
    if len(runs) < 2:
        return False
    paths = {tuple(tool.name for tool in run.result.tool_calls) for run in runs}
    return len(paths) > 1


def build_test_report(test_name: str, runs: list[TestRun]) -> TestReport:
    total_runs = len(runs)
    passed_runs = sum(1 for run in runs if run.passed)
    failed_runs = total_runs - passed_runs
    average_steps = sum(run.result.steps for run in runs) / total_runs if total_runs else 0.0
    failures = Counter()
    for run in runs:
        if run.error and not run.assertions:
            failures[run.error] += 1
        for assertion in run.assertions:
            if not assertion.passed:
                failures[assertion.message] += 1
    failure_reasons = [f"{message} ({count}/{total_runs} runs)" for message, count in failures.most_common()]

    latencies = [run.result.latency for run in runs if run.result.latency is not None]
    average_latency = sum(latencies) / len(latencies) if latencies else None
    costs = [run.result.cost for run in runs if run.result.cost is not None]
    average_cost = sum(costs) / len(costs) if costs else None

    return TestReport(
        test_name=test_name,
        total_runs=total_runs,
        passed_runs=passed_runs,
        failed_runs=failed_runs,
        success_rate=(passed_runs / total_runs) * 100 if total_runs else 0.0,
        failure_reasons=failure_reasons,
        average_steps=average_steps,
        tool_presence=_build_tool_presence(runs),
        common_tool_paths=_build_common_tool_paths(runs),
        failure_categories=_build_failure_categories(runs),
        flakiness_score=_compute_flakiness_score(runs),
        unstable_tool_paths=_has_unstable_tool_paths(runs),
        average_latency=average_latency,
        average_cost=average_cost,
    )


def new_session_report(reports: list[TestReport], suite_id: str | None = None) -> SessionReport:
    return SessionReport(
        created_at=datetime.now(timezone.utc).isoformat(),
        reports=reports,
        suite_id=suite_id,
    )


def render_markdown_report(session_data: SessionReport | dict[str, Any]) -> str:
    if isinstance(session_data, SessionReport):
        data = session_data.to_dict()
    else:
        data = session_data

    lines = [
        "# Invarium Report",
        "",
        f"- Created at: `{data['created_at']}`",
    ]
    if data.get("suite_id"):
        lines.append(f"- Suite: `{data['suite_id']}`")
    if data.get("trace_file"):
        lines.append(f"- Trace file: `{data['trace_file']}`")
    lines.append("")

    for report in data["reports"]:
        lines.extend(
            [
                f"## {report['test_name']}",
                "",
                f"- Runs: {report['total_runs']}",
                f"- Passed: {report['passed_runs']}",
                f"- Failed: {report['failed_runs']}",
                f"- Success rate: {report['success_rate']:.1f}%",
                f"- Average steps: {report['average_steps']:.1f}",
            ]
        )
        if report.get("average_latency") is not None:
            lines.append(f"- Average latency: {report['average_latency']:.2f}s")
        if report.get("average_cost") is not None:
            lines.append(f"- Average cost: ${report['average_cost']:.4f}")
        flakiness = report.get("flakiness_score", 0.0)
        if flakiness > 0:
            label = "high" if flakiness >= 0.5 else "moderate" if flakiness >= 0.2 else "low"
            lines.append(f"- Flakiness: {flakiness:.3f} ({label})")
        if report.get("unstable_tool_paths"):
            lines.append("- Tool paths: unstable across runs")
        failure_categories = report.get("failure_categories", {})
        if failure_categories:
            lines.append("")
            lines.append("### Failure Categories")
            lines.append("")
            for cat, count in failure_categories.items():
                lines.append(f"- `{cat}`: {count}")
        if report["failure_reasons"]:
            lines.append("")
            lines.append("### Failures")
            lines.append("")
            for reason in report["failure_reasons"]:
                lines.append(f"- {reason}")
        lines.append("")

    comparison = data.get("baseline_comparison", {})
    if comparison:
        lines.append("## Baseline Comparison")
        lines.append("")
        lines.append(f"- Summary: {comparison['summary']}")
        matched_tests = comparison.get("matched_tests", [])
        current_only_tests = comparison.get("current_only_tests", [])
        baseline_only_tests = comparison.get("baseline_only_tests", [])
        if matched_tests:
            lines.append(f"- Matched tests: {', '.join(f'`{name}`' for name in matched_tests)}")
        if current_only_tests:
            lines.append(
                "- Current-only tests: "
                + ", ".join(f"`{name}`" for name in current_only_tests)
            )
        if baseline_only_tests:
            lines.append(
                "- Baseline-only tests: "
                + ", ".join(f"`{name}`" for name in baseline_only_tests)
            )
        regressions = comparison.get("regressions", [])
        if regressions:
            lines.append("")
            lines.append("### Regressions")
            lines.append("")
            for regression in regressions:
                lines.append(
                    "- "
                    f"{regression['test_name']}: "
                    f"{regression['previous_success_rate']:.1f}% -> "
                    f"{regression['current_success_rate']:.1f}% "
                    f"(step delta {regression['step_delta']:+.1f})"
                )
                if regression.get("latency_delta") is not None:
                    lines.append(f"  - Latency delta: {regression['latency_delta']:+.2f}s")
                if regression.get("cost_delta") is not None:
                    lines.append(f"  - Cost delta: ${regression['cost_delta']:+.4f}")
                failure_categories = regression.get("failure_categories", {})
                if failure_categories:
                    cats_str = ", ".join(f"`{c}` x{n}" for c, n in failure_categories.items())
                    lines.append(f"  - Failure categories: {cats_str}")
                primary_path_change = regression.get("primary_path_change")
                if primary_path_change:
                    previous_path = " -> ".join(primary_path_change["previous_path"]) or "(no tools)"
                    current_path = " -> ".join(primary_path_change["current_path"]) or "(no tools)"
                    lines.append(
                        "  - Primary tool path changed: "
                        f"`{previous_path}` ({primary_path_change['previous_rate']:.1f}%) -> "
                        f"`{current_path}` ({primary_path_change['current_rate']:.1f}%)"
                    )
                for drop in regression.get("tool_coverage_drops", []):
                    lines.append(
                        "  - Tool coverage dropped: "
                        f"`{drop['tool_name']}` "
                        f"{drop['previous_rate']:.1f}% -> {drop['current_rate']:.1f}%"
                    )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_github_step_summary(markdown: str, summary_path: str | None) -> bool:
    if not summary_path:
        return False
    path = Path(summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return True
