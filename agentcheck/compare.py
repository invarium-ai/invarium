from __future__ import annotations

from typing import Any


def _tool_coverage_drops(
    current_report: dict[str, Any],
    baseline_report: dict[str, Any],
) -> list[dict[str, Any]]:
    current_tools = current_report.get("tool_presence", {})
    baseline_tools = baseline_report.get("tool_presence", {})
    drops: list[dict[str, Any]] = []
    for tool_name in sorted(set(current_tools) | set(baseline_tools)):
        previous_rate = float(baseline_tools.get(tool_name, 0.0))
        current_rate = float(current_tools.get(tool_name, 0.0))
        if current_rate >= previous_rate:
            continue
        drops.append(
            {
                "tool_name": tool_name,
                "previous_rate": previous_rate,
                "current_rate": current_rate,
                "delta": current_rate - previous_rate,
            }
        )
    return sorted(drops, key=lambda item: (item["delta"], item["tool_name"]))


def _primary_path_change(
    current_report: dict[str, Any],
    baseline_report: dict[str, Any],
) -> dict[str, Any] | None:
    current_paths = current_report.get("common_tool_paths", [])
    baseline_paths = baseline_report.get("common_tool_paths", [])
    current_primary = current_paths[0] if current_paths else None
    baseline_primary = baseline_paths[0] if baseline_paths else None

    current_path = current_primary.get("path", []) if current_primary else []
    baseline_path = baseline_primary.get("path", []) if baseline_primary else []
    if current_path == baseline_path:
        return None

    if not current_primary and not baseline_primary:
        return None

    return {
        "previous_path": baseline_path,
        "current_path": current_path,
        "previous_rate": float(baseline_primary.get("rate", 0.0)) if baseline_primary else 0.0,
        "current_rate": float(current_primary.get("rate", 0.0)) if current_primary else 0.0,
    }


def compare_reports(
    current: list[dict[str, Any]],
    baseline: list[dict[str, Any]] | None,
    *,
    current_suite: str | None = None,
    baseline_suite: str | None = None,
) -> dict[str, Any]:
    if baseline is None:
        return {
            "available": False,
            "suite_mismatch": False,
            "regressions": [],
            "matched_tests": [],
            "current_only_tests": [],
            "baseline_only_tests": [],
            "summary": "No baseline found.",
        }

    if current_suite and baseline_suite and current_suite != baseline_suite:
        return {
            "available": True,
            "suite_mismatch": True,
            "regressions": [],
            "matched_tests": [],
            "current_only_tests": [],
            "baseline_only_tests": [],
            "summary": (
                "Baseline suite mismatch: "
                f"current `{current_suite}` vs baseline `{baseline_suite}`. "
                "Suite identities must match exactly. "
                "Run `agentcheck bless <path>` for this suite."
            ),
        }

    baseline_map = {report["test_name"]: report for report in baseline}
    current_names = {report["test_name"] for report in current}
    baseline_names = set(baseline_map)
    overlapping_names = current_names & baseline_names
    current_only_tests = sorted(current_names - baseline_names)
    baseline_only_tests = sorted(baseline_names - current_names)

    if not overlapping_names:
        return {
            "available": True,
            "suite_mismatch": True,
            "regressions": [],
            "matched_tests": [],
            "current_only_tests": current_only_tests,
            "baseline_only_tests": baseline_only_tests,
            "summary": (
                "Baseline suite mismatch: "
                f"current `{current_suite}` vs baseline `{baseline_suite}`. "
                "The reports do not share any test names. "
                "Run `agentcheck bless <path>` for this suite."
            ),
        }
    regressions: list[dict[str, Any]] = []
    for report in current:
        previous = baseline_map.get(report["test_name"])
        if previous is None:
            continue
        if report["success_rate"] < previous["success_rate"]:
            cur_latency = report.get("average_latency")
            prev_latency = previous.get("average_latency")
            latency_delta = (cur_latency - prev_latency) if cur_latency is not None and prev_latency is not None else None
            cur_cost = report.get("average_cost")
            prev_cost = previous.get("average_cost")
            cost_delta = (cur_cost - prev_cost) if cur_cost is not None and prev_cost is not None else None
            regressions.append(
                {
                    "test_name": report["test_name"],
                    "previous_success_rate": previous["success_rate"],
                    "current_success_rate": report["success_rate"],
                    "step_delta": report["average_steps"] - previous.get("average_steps", 0.0),
                    "latency_delta": latency_delta,
                    "cost_delta": cost_delta,
                    "tool_coverage_drops": _tool_coverage_drops(report, previous),
                    "primary_path_change": _primary_path_change(report, previous),
                    "failure_categories": report.get("failure_categories", {}),
                }
            )
    matched_tests = sorted(overlapping_names)
    if regressions:
        summary = f"Regression detected in {len(regressions)} of {len(matched_tests)} matched test(s)."
    else:
        summary = f"No regression detected across {len(matched_tests)} matched test(s)."
    return {
        "available": True,
        "suite_mismatch": False,
        "regressions": regressions,
        "matched_tests": matched_tests,
        "current_only_tests": current_only_tests,
        "baseline_only_tests": baseline_only_tests,
        "summary": summary,
    }
