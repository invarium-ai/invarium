from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .baseline import load_baseline, save_baseline
from .compare import compare_reports
from .contracts import CONTRACT_FILE, _default_contract, load_contract, save_contract, validate_contract
from .discovery import collect_registered_tests, discover_test_files, import_test_file
from .report import SessionReport, render_markdown_report, write_github_step_summary
from .runners import run_test_suite
from .storage import REPORT_DIR, TRACE_DIR, ensure_artifact_dirs, read_json, write_json


EXIT_SUCCESS = 0
EXIT_BEHAVIOR_FAILED = 1
EXIT_REGRESSION = 2
EXIT_CONFIG_ERROR = 3

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentcheck")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("test", "bless", "compare", "report"):
        subparser = subparsers.add_parser(command)
        if command in {"test", "bless"}:
            subparser.add_argument("path", nargs="?", default=".")
            subparser.add_argument("--fail-on-regression", action="store_true")

    contract_parser = subparsers.add_parser("contract")
    contract_subparsers = contract_parser.add_subparsers(dest="contract_command", required=True)

    init_parser = contract_subparsers.add_parser("init")
    init_parser.add_argument("name", nargs="?", default="my_agent", help="Agent name for the contract")
    init_parser.add_argument("--output", default=None, help=f"Output file path (default: {CONTRACT_FILE})")

    validate_parser = contract_subparsers.add_parser("validate")
    validate_parser.add_argument("path", nargs="?", default=CONTRACT_FILE, help="Path to contract JSON file")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ensure_artifact_dirs()

    if args.command in {"test", "bless"}:
        return _run_tests(Path(args.path), bless=args.command == "bless", fail_on_regression=args.fail_on_regression)
    if args.command == "compare":
        return _compare_only()
    if args.command == "report":
        return _report_only()
    if args.command == "contract":
        if args.contract_command == "init":
            return _contract_init(args.name, args.output)
        if args.contract_command == "validate":
            return _contract_validate(args.path)
    return EXIT_CONFIG_ERROR


def _run_tests(root: Path, *, bless: bool, fail_on_regression: bool) -> int:
    _load_tests(root)
    definitions = collect_registered_tests()
    if not definitions:
        print("No AgentCheck tests found.")
        return EXIT_CONFIG_ERROR

    reports, session, trace_payload = run_test_suite(definitions)
    session.suite_id = str(root.resolve())
    current_data = [report.to_dict() for report in reports]
    baseline_data = load_baseline(session.suite_id)
    comparison = compare_reports(
        current_data,
        baseline_data["reports"] if baseline_data else None,
        current_suite=session.suite_id,
        baseline_suite=baseline_data.get("suite_id") if baseline_data else None,
    )
    session.baseline_comparison = comparison

    trace_path = TRACE_DIR / "latest.json"
    report_path = REPORT_DIR / "latest.json"
    markdown_report_path = REPORT_DIR / "latest.md"
    session.trace_file = str(trace_path)
    session.markdown_report_file = str(markdown_report_path)
    write_json(trace_path, trace_payload)
    write_json(report_path, session.to_dict())
    markdown = render_markdown_report(session)
    markdown_report_path.write_text(markdown, encoding="utf-8")
    summary_written = write_github_step_summary(markdown, os.environ.get("GITHUB_STEP_SUMMARY"))
    _print_session_summary(session)
    if summary_written:
        print(f"GitHub step summary: {os.environ['GITHUB_STEP_SUMMARY']}")

    if bless:
        baseline_path = save_baseline({"suite_id": session.suite_id, "reports": current_data}, session.suite_id)
        print(f"\nBaseline saved to {baseline_path}")

    any_behavior_failures = any(report.failed_runs for report in reports)
    any_regression = bool(comparison["regressions"])
    if comparison.get("suite_mismatch") and fail_on_regression:
        return EXIT_CONFIG_ERROR
    if fail_on_regression and any_regression:
        return EXIT_REGRESSION
    if any_behavior_failures:
        return EXIT_BEHAVIOR_FAILED
    return EXIT_SUCCESS


def _contract_init(name: str, output: str | None) -> int:
    output_path = Path(output) if output else Path(CONTRACT_FILE)
    if output_path.exists():
        print(f"Contract file already exists: {output_path}")
        print("Delete it or specify a different path with --output.")
        return EXIT_CONFIG_ERROR
    contract = _default_contract(name)
    save_contract(contract, output_path)
    print(_style("Contract initialized", bold=True))
    print(_kv("File", str(output_path)))
    print(_kv("Name", contract.name))
    print("")
    print("Edit the file to describe your agent's expected behavior.")
    print(f"Then run: agentcheck contract validate {output_path}")
    return EXIT_SUCCESS


def _contract_validate(path: str) -> int:
    contract_path = Path(path)
    if not contract_path.exists():
        print(f"Contract file not found: {contract_path}")
        print(f"Create one with: agentcheck contract init")
        return EXIT_CONFIG_ERROR
    try:
        contract = load_contract(contract_path)
    except Exception as exc:
        print(f"{_badge('ERROR', color='red')} Failed to parse contract: {exc}")
        return EXIT_CONFIG_ERROR

    errors = validate_contract(contract)
    if errors:
        print(f"{_badge('INVALID', color='red')} {contract_path}")
        for error in errors:
            print(f"  - [{error.field}] {error.message}")
        return EXIT_BEHAVIOR_FAILED

    print(f"{_badge('VALID', color='green')} {contract_path}")
    print(_kv("Name", contract.name))
    if contract.description:
        print(_kv("Description", contract.description))
    if contract.expected_tools:
        print(_kv("Tools", ", ".join(contract.expected_tools)))
    if contract.required_tool_order:
        print(_kv("Order", " -> ".join(contract.required_tool_order)))
    if contract.step_budget is not None:
        print(_kv("Step budget", str(contract.step_budget)))
    if contract.scenario_tags:
        print(_kv("Tags", ", ".join(contract.scenario_tags)))
    return EXIT_SUCCESS


def _compare_only() -> int:
    latest_report = REPORT_DIR / "latest.json"
    report_data = read_json(latest_report) if latest_report.exists() else None
    baseline = load_baseline(report_data.get("suite_id") if report_data else None)
    if not latest_report.exists() or baseline is None:
        print("Latest report or baseline is missing.")
        return EXIT_CONFIG_ERROR
    comparison = compare_reports(
        report_data["reports"],
        baseline["reports"],
        current_suite=report_data.get("suite_id"),
        baseline_suite=baseline.get("suite_id"),
    )
    _print_comparison(comparison)
    if comparison.get("suite_mismatch"):
        return EXIT_CONFIG_ERROR
    return EXIT_REGRESSION if comparison["regressions"] else EXIT_SUCCESS


def _report_only() -> int:
    latest_report = REPORT_DIR / "latest.json"
    if not latest_report.exists():
        print("No report found. Run `agentcheck test` first.")
        return EXIT_CONFIG_ERROR
    report_data = read_json(latest_report)
    _print_session_summary_dict(report_data)
    return EXIT_SUCCESS


def _load_tests(root: Path) -> None:
    for file_path in discover_test_files(root):
        import_test_file(file_path)


def _print_session_summary(session: SessionReport) -> None:
    _print_session_summary_dict(session.to_dict())


def _print_session_summary_dict(session_data: dict) -> None:
    rendered = _render_session_summary_dict(session_data)
    if rendered:
        print(rendered)


def _print_comparison(comparison: dict) -> None:
    rendered = _render_comparison(comparison)
    if rendered:
        print(rendered)


def _supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"


def _style(text: str, *, color: str | None = None, bold: bool = False) -> str:
    if not _supports_color():
        return text
    parts: list[str] = []
    if bold:
        parts.append(ANSI_BOLD)
    if color:
        parts.append(ANSI_COLORS[color])
    return "".join(parts) + text + ANSI_RESET


def _badge(label: str, *, color: str) -> str:
    return _style(f"[{label}]", color=color, bold=True)


def _kv(label: str, value: str, *, indent: int = 2, width: int = 12) -> str:
    return f"{' ' * indent}{label.ljust(width)} {value}"


def _format_tool_presence(report: dict) -> str | None:
    tool_presence = report.get("tool_presence", {})
    if not tool_presence:
        return None
    return ", ".join(
        f"{tool_name} {rate:.1f}%"
        for tool_name, rate in sorted(tool_presence.items())
    )


def _format_primary_path(report: dict) -> str | None:
    common_tool_paths = report.get("common_tool_paths", [])
    if not common_tool_paths:
        return None
    primary_path = common_tool_paths[0]
    path_text = " -> ".join(primary_path.get("path", [])) or "(no tools)"
    return f"{path_text} ({primary_path.get('rate', 0.0):.1f}%)"


def _render_session_summary_dict(session_data: dict) -> str:
    reports = session_data.get("reports", [])
    comparison = session_data.get("baseline_comparison", {})
    regression_names = {item["test_name"] for item in comparison.get("regressions", [])}
    lines = [_style("AgentCheck", bold=True)]

    if session_data.get("suite_id"):
        lines.append(_kv("Suite", str(session_data["suite_id"])))
    lines.append(_kv("Reports", str(len(reports))))
    if session_data.get("trace_file"):
        lines.append(_kv("Trace", str(session_data["trace_file"])))
    if session_data.get("markdown_report_file"):
        lines.append(_kv("Markdown", str(session_data["markdown_report_file"])))

    for report in reports:
        lines.append("")
        status_label = "FAIL" if report["failed_runs"] else "PASS"
        status_color = "red" if report["failed_runs"] else "green"
        if report["test_name"] in regression_names and not report["failed_runs"]:
            status_label = "REGRESSION"
            status_color = "yellow"
        lines.append(f"{_badge(status_label, color=status_color)} {report['test_name']}")
        lines.append(_kv("Runs", str(report["total_runs"])))
        lines.append(_kv("Passed", str(report["passed_runs"])))
        lines.append(_kv("Failed", str(report["failed_runs"])))
        lines.append(_kv("Success", f"{report['success_rate']:.1f}%"))
        lines.append(_kv("Avg steps", f"{report['average_steps']:.1f}"))

        if report.get("average_latency") is not None:
            lines.append(_kv("Latency", f"{report['average_latency']:.2f}s"))
        if report.get("average_cost") is not None:
            lines.append(_kv("Cost", f"${report['average_cost']:.4f}"))
        flakiness = report.get("flakiness_score", 0.0)
        if flakiness > 0:
            label = "high" if flakiness >= 0.5 else "moderate" if flakiness >= 0.2 else "low"
            lines.append(_kv("Flakiness", f"{flakiness:.3f} ({label})"))
        if report.get("unstable_tool_paths"):
            lines.append(_kv("Tool paths", "unstable"))
        tool_summary = _format_tool_presence(report)
        if tool_summary:
            lines.append(_kv("Tools", tool_summary))
        primary_path = _format_primary_path(report)
        if primary_path:
            lines.append(_kv("Path", primary_path))

        failure_categories = report.get("failure_categories", {})
        if failure_categories:
            lines.append(_kv("Fail cats", ", ".join(f"{c}:{n}" for c, n in failure_categories.items())))

        if report["failure_reasons"]:
            lines.append(_kv("Failures", ""))
            for reason in report["failure_reasons"]:
                lines.append(f"    - {reason}")

    comparison_render = _render_comparison(comparison)
    if comparison_render:
        lines.append("")
        lines.extend(comparison_render.splitlines())

    return "\n".join(lines)


def _render_comparison(comparison: dict) -> str:
    if not comparison:
        return ""

    status_label = "WARN" if comparison.get("suite_mismatch") else ("REGRESSION" if comparison.get("regressions") else "OK")
    status_color = "yellow" if status_label in {"WARN", "REGRESSION"} else "green"
    lines = [f"{_badge(status_label, color=status_color)} Baseline comparison"]
    lines.append(_kv("Summary", comparison["summary"]))

    matched_tests = comparison.get("matched_tests", [])
    current_only_tests = comparison.get("current_only_tests", [])
    baseline_only_tests = comparison.get("baseline_only_tests", [])
    if matched_tests:
        lines.append(_kv("Matched", ", ".join(matched_tests)))
    if current_only_tests:
        lines.append(_kv("Current only", ", ".join(current_only_tests)))
    if baseline_only_tests:
        lines.append(_kv("Baseline only", ", ".join(baseline_only_tests)))

    for regression in comparison.get("regressions", []):
        lines.append("")
        lines.append(f"{_badge('REGRESSION', color='yellow')} {regression['test_name']}")
        lines.append(
            _kv(
                "Success",
                f"{regression['previous_success_rate']:.1f}% -> {regression['current_success_rate']:.1f}%",
            )
        )
        lines.append(_kv("Step delta", f"{regression['step_delta']:+.1f}"))
        if regression.get("latency_delta") is not None:
            lines.append(_kv("Latency", f"{regression['latency_delta']:+.2f}s"))
        if regression.get("cost_delta") is not None:
            lines.append(_kv("Cost", f"${regression['cost_delta']:+.4f}"))
        failure_categories = regression.get("failure_categories", {})
        if failure_categories:
            lines.append(_kv("Failure cats", ", ".join(f"{c}:{n}" for c, n in failure_categories.items())))
        primary_path_change = regression.get("primary_path_change")
        if primary_path_change:
            previous_path = " -> ".join(primary_path_change["previous_path"]) or "(no tools)"
            current_path = " -> ".join(primary_path_change["current_path"]) or "(no tools)"
            lines.append(
                _kv(
                    "Path",
                    f"{previous_path} ({primary_path_change['previous_rate']:.1f}%) -> "
                    f"{current_path} ({primary_path_change['current_rate']:.1f}%)",
                )
            )
        for drop in regression.get("tool_coverage_drops", []):
            lines.append(
                _kv(
                    "Tool drop",
                    f"{drop['tool_name']} {drop['previous_rate']:.1f}% -> {drop['current_rate']:.1f}%",
                )
            )

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
