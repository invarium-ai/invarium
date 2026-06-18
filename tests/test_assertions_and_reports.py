from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from invarium import AgentResult, ToolCall, expect
from invarium.baseline import load_baseline, save_baseline, suite_baseline_path
from invarium.compare import compare_reports
from invarium.report import (
    TestRun as AgentTestRun,
    build_test_report,
    new_run_id,
    render_markdown_report,
    write_github_step_summary,
)


def test_tool_count_assertions_pass_in_collected_mode():
    result = AgentResult(
        input="Research Invarium",
        final_output="Done",
        tool_calls=[
            ToolCall(name="search_docs", args={"query": "Invarium"}),
            ToolCall(name="search_docs", args={"query": "pytest for agents"}),
            ToolCall(name="summarize_notes", args={"length": "short"}),
        ],
        steps=3,
    )

    check = expect(result, collect=True)
    check.used_tool_times("summarize_notes", 1)
    check.used_tool_at_least("search_docs", 2)
    check.used_tool_at_most("search_docs", 2)
    check.verify()


def test_markdown_report_render_includes_summary_and_failures():
    markdown = render_markdown_report(
        {
            "created_at": "2026-04-28T00:00:00Z",
            "suite_id": "framework_examples",
            "trace_file": ".invarium/traces/latest.json",
            "markdown_report_file": ".invarium/reports/latest.md",
            "reports": [
                {
                    "test_name": "test_booking_agent",
                    "total_runs": 5,
                    "passed_runs": 3,
                    "failed_runs": 2,
                    "success_rate": 60.0,
                    "failure_reasons": [
                        "Expected tool `booking_tool` to be called, but saw ['restaurant_search']. (2/5 runs)"
                    ],
                    "average_steps": 2.4,
                    "regression": False,
                }
            ],
            "baseline_comparison": {
                "summary": "Regression detected in 1 of 1 matched test(s).",
                "matched_tests": ["test_booking_agent"],
                "current_only_tests": [],
                "baseline_only_tests": [],
                "regressions": [
                    {
                        "test_name": "test_booking_agent",
                        "previous_success_rate": 100.0,
                        "current_success_rate": 60.0,
                        "step_delta": 0.4,
                        "primary_path_change": {
                            "previous_path": ["restaurant_search", "booking_tool"],
                            "current_path": ["restaurant_search"],
                            "previous_rate": 100.0,
                            "current_rate": 60.0,
                        },
                        "tool_coverage_drops": [
                            {
                                "tool_name": "booking_tool",
                                "previous_rate": 100.0,
                                "current_rate": 60.0,
                                "delta": -40.0,
                            }
                        ],
                    }
                ],
            },
        }
    )

    assert "# Invarium Report" in markdown
    assert "- Suite: `framework_examples`" in markdown
    assert "## test_booking_agent" in markdown
    assert "### Failures" in markdown
    assert "Regression detected in 1 of 1 matched test(s)." in markdown
    assert "- Matched tests: `test_booking_agent`" in markdown
    assert "### Regressions" in markdown
    assert "100.0% -> 60.0%" in markdown
    assert "Primary tool path changed" in markdown
    assert "Tool coverage dropped: `booking_tool` 100.0% -> 60.0%" in markdown


def test_compare_reports_flags_suite_mismatch():
    comparison = compare_reports(
        [{"test_name": "test_booking_agent", "success_rate": 100.0, "average_steps": 2.0}],
        [{"test_name": "test_langgraph_research_agent", "success_rate": 100.0, "average_steps": 3.0}],
        current_suite="examples",
        baseline_suite="framework_examples",
    )

    assert comparison["suite_mismatch"] is True
    assert comparison["regressions"] == []
    assert "Baseline suite mismatch" in comparison["summary"]
    assert comparison["matched_tests"] == []


def test_compare_reports_flags_suite_mismatch_even_when_test_names_overlap():
    comparison = compare_reports(
        [{"test_name": "test_booking_agent", "success_rate": 0.0, "average_steps": 2.0}],
        [{"test_name": "test_booking_agent", "success_rate": 100.0, "average_steps": 2.0}],
        current_suite="regression_examples",
        baseline_suite="examples",
    )

    assert comparison["suite_mismatch"] is True
    assert comparison["regressions"] == []


def test_compare_reports_allows_legacy_comparison_when_suite_ids_are_missing():
    comparison = compare_reports(
        [{"test_name": "test_booking_agent", "success_rate": 0.0, "average_steps": 2.0}],
        [{"test_name": "test_booking_agent", "success_rate": 100.0, "average_steps": 2.0}],
    )

    assert comparison["suite_mismatch"] is False
    assert len(comparison["regressions"]) == 1
    assert comparison["matched_tests"] == ["test_booking_agent"]
    assert comparison["current_only_tests"] == []
    assert comparison["baseline_only_tests"] == []


def test_compare_reports_tracks_unmatched_tests():
    comparison = compare_reports(
        [
            {"test_name": "test_booking_agent", "success_rate": 100.0, "average_steps": 2.0},
            {"test_name": "test_research_agent", "success_rate": 100.0, "average_steps": 3.0},
        ],
        [
            {"test_name": "test_booking_agent", "success_rate": 100.0, "average_steps": 2.0},
            {"test_name": "test_weather_agent", "success_rate": 100.0, "average_steps": 4.0},
        ],
    )

    assert comparison["suite_mismatch"] is False
    assert comparison["matched_tests"] == ["test_booking_agent"]
    assert comparison["current_only_tests"] == ["test_research_agent"]
    assert comparison["baseline_only_tests"] == ["test_weather_agent"]
    assert comparison["summary"] == "No regression detected across 1 matched test(s)."


def test_build_test_report_tracks_tool_presence_and_common_paths():
    runs = [
        AgentTestRun(
            test_name="test_booking_agent",
            run_id=new_run_id(),
            result=AgentResult(
                input="Book dinner",
                final_output="Done",
                tool_calls=[
                    ToolCall(name="restaurant_search"),
                    ToolCall(name="booking_tool"),
                ],
                steps=2,
            ),
        ),
        AgentTestRun(
            test_name="test_booking_agent",
            run_id=new_run_id(),
            result=AgentResult(
                input="Book dinner",
                final_output="Done",
                tool_calls=[ToolCall(name="restaurant_search")],
                steps=1,
            ),
            passed=False,
            error="booking_tool missing",
        ),
    ]

    report = build_test_report("test_booking_agent", runs)

    assert report.tool_presence == {
        "booking_tool": 50.0,
        "restaurant_search": 100.0,
    }
    assert report.common_tool_paths == [
        {
            "path": ["restaurant_search", "booking_tool"],
            "count": 1,
            "rate": 50.0,
        },
        {
            "path": ["restaurant_search"],
            "count": 1,
            "rate": 50.0,
        },
    ]


def test_compare_reports_includes_behavior_deltas_for_regressions():
    comparison = compare_reports(
        [
            {
                "test_name": "test_booking_agent",
                "success_rate": 60.0,
                "average_steps": 2.4,
                "tool_presence": {
                    "restaurant_search": 100.0,
                    "booking_tool": 60.0,
                },
                "common_tool_paths": [
                    {"path": ["restaurant_search"], "count": 3, "rate": 60.0}
                ],
            }
        ],
        [
            {
                "test_name": "test_booking_agent",
                "success_rate": 100.0,
                "average_steps": 2.0,
                "tool_presence": {
                    "restaurant_search": 100.0,
                    "booking_tool": 100.0,
                },
                "common_tool_paths": [
                    {
                        "path": ["restaurant_search", "booking_tool"],
                        "count": 5,
                        "rate": 100.0,
                    }
                ],
            }
        ],
    )

    assert comparison["summary"] == "Regression detected in 1 of 1 matched test(s)."
    regression = comparison["regressions"][0]
    assert regression["test_name"] == "test_booking_agent"
    assert regression["previous_success_rate"] == 100.0
    assert regression["current_success_rate"] == 60.0
    assert abs(regression["step_delta"] - 0.4) < 1e-9
    assert regression["latency_delta"] is None
    assert regression["cost_delta"] is None
    assert regression["failure_categories"] == {}
    assert regression["tool_coverage_drops"] == [
        {
            "tool_name": "booking_tool",
            "previous_rate": 100.0,
            "current_rate": 60.0,
            "delta": -40.0,
        }
    ]
    assert regression["primary_path_change"] == {
        "previous_path": ["restaurant_search", "booking_tool"],
        "current_path": ["restaurant_search"],
        "previous_rate": 100.0,
        "current_rate": 60.0,
    }


def test_suite_baselines_are_isolated(monkeypatch):
    workspace_tmp = Path(".build-tmp") / f"baseline-test-{uuid4().hex}"
    monkeypatch.setattr("invarium.storage.BASELINE_DIR", workspace_tmp)
    monkeypatch.setattr("invarium.baseline.BASELINE_DIR", workspace_tmp)
    monkeypatch.setattr("invarium.baseline.BASELINE_FILE", workspace_tmp / "latest.json")

    first_suite = str(workspace_tmp / "examples")
    second_suite = str(workspace_tmp / "framework_examples")
    first_data = {"suite_id": first_suite, "reports": [{"test_name": "test_booking_agent"}]}
    second_data = {"suite_id": second_suite, "reports": [{"test_name": "test_langgraph_agent"}]}

    first_path = save_baseline(first_data, first_suite)
    second_path = save_baseline(second_data, second_suite)

    assert first_path != second_path
    assert first_path == suite_baseline_path(first_suite)
    assert second_path == suite_baseline_path(second_suite)
    assert load_baseline(first_suite) == first_data
    assert load_baseline(second_suite) == second_data
    assert load_baseline(str(workspace_tmp / "missing_suite")) is None


def test_write_github_step_summary_writes_markdown():
    summary_path = Path(".build-tmp") / f"step-summary-{uuid4().hex}.md"
    markdown = "# Invarium Report\n"

    written = write_github_step_summary(markdown, str(summary_path))

    assert written is True
    assert summary_path.read_text(encoding="utf-8") == markdown


# ── New assertions ──────────────────────────────────────────────────────────

def test_used_any_tool_passes_when_at_least_one_tool_used():
    result = AgentResult(
        input="q", final_output="done",
        tool_calls=[ToolCall(name="search")], steps=1,
    )
    expect(result).used_any_tool().verify()


def test_used_any_tool_fails_when_no_tools_used():
    result = AgentResult(input="q", final_output="done", steps=0)
    import pytest
    with pytest.raises(Exception):
        expect(result).used_any_tool().verify()


def test_final_output_matches_pattern_passes():
    result = AgentResult(input="q", final_output="Order #12345 confirmed", steps=1)
    expect(result).final_output_matches_pattern(r"Order #\d+").verify()


def test_final_output_matches_pattern_fails():
    result = AgentResult(input="q", final_output="no match here", steps=1)
    import pytest
    with pytest.raises(Exception):
        expect(result).final_output_matches_pattern(r"Order #\d+").verify()


def test_tool_succeeded_passes_when_tool_succeeded():
    result = AgentResult(
        input="q", final_output="done",
        tool_calls=[ToolCall(name="book", success=True)], steps=1,
    )
    expect(result).tool_succeeded("book").verify()


def test_tool_succeeded_fails_when_tool_failed():
    result = AgentResult(
        input="q", final_output="done",
        tool_calls=[ToolCall(name="book", success=False)], steps=1,
    )
    import pytest
    with pytest.raises(Exception):
        expect(result).tool_succeeded("book").verify()


# ── Failure taxonomy ────────────────────────────────────────────────────────

def test_assertion_record_has_category_on_failure():
    result = AgentResult(input="q", final_output="done", steps=0)
    check = expect(result, collect=True)
    check.used_tool("missing_tool")
    record = check.records[0]
    assert not record.passed
    assert record.category == "missing_required_tool"


def test_assertion_record_has_no_category_on_pass():
    result = AgentResult(
        input="q", final_output="done",
        tool_calls=[ToolCall(name="search")], steps=1,
    )
    check = expect(result, collect=True)
    check.used_tool("search")
    record = check.records[0]
    assert record.passed
    assert record.category is None


def test_build_test_report_aggregates_failure_categories():
    from invarium.assertions import AssertionRecord
    from invarium.report import TestRun as AgentTestRun, build_test_report, new_run_id

    failed_run = AgentTestRun(
        test_name="t",
        run_id=new_run_id(),
        result=AgentResult(input="q", final_output="done", steps=1),
        assertions=[
            AssertionRecord(name="used_tool", passed=False, message="missing", category="missing_required_tool"),
            AssertionRecord(name="steps_less_than", passed=False, message="exceeded", category="step_budget_exceeded"),
        ],
        passed=False,
        error="missing",
    )
    report = build_test_report("t", [failed_run])
    assert report.failure_categories.get("missing_required_tool", 0) >= 1
    assert report.failure_categories.get("step_budget_exceeded", 0) >= 1


# ── Flakiness ───────────────────────────────────────────────────────────────

def test_flakiness_score_is_zero_for_all_passing():
    runs = [
        AgentTestRun(
            test_name="t", run_id=new_run_id(),
            result=AgentResult(input="q", final_output="done",
                               tool_calls=[ToolCall(name="search")], steps=1),
            passed=True,
        )
        for _ in range(5)
    ]
    report = build_test_report("t", runs)
    assert report.flakiness_score == 0.0
    assert report.unstable_tool_paths is False


def test_flakiness_score_is_nonzero_for_mixed_results():
    pass_run = AgentTestRun(
        test_name="t", run_id=new_run_id(),
        result=AgentResult(input="q", final_output="done",
                           tool_calls=[ToolCall(name="search")], steps=1),
        passed=True,
    )
    fail_run = AgentTestRun(
        test_name="t", run_id=new_run_id(),
        result=AgentResult(input="q", final_output="done", steps=0),
        passed=False,
        error="oops",
    )
    report = build_test_report("t", [pass_run, fail_run])
    assert report.flakiness_score > 0.0


def test_unstable_tool_paths_detected():
    run_a = AgentTestRun(
        test_name="t", run_id=new_run_id(),
        result=AgentResult(input="q", final_output="done",
                           tool_calls=[ToolCall(name="a"), ToolCall(name="b")], steps=2),
        passed=True,
    )
    run_b = AgentTestRun(
        test_name="t", run_id=new_run_id(),
        result=AgentResult(input="q", final_output="done",
                           tool_calls=[ToolCall(name="a")], steps=1),
        passed=True,
    )
    report = build_test_report("t", [run_a, run_b])
    assert report.unstable_tool_paths is True


# ── Contracts ───────────────────────────────────────────────────────────────

def test_valid_contract_passes_validation():
    from invarium.contracts import AgentContract, validate_contract
    contract = AgentContract(
        name="search_agent",
        expected_tools=["search", "summarize"],
        required_tool_order=["search", "summarize"],
        step_budget=5,
        scenario_tags=["happy_path"],
    )
    errors = validate_contract(contract)
    assert errors == []


def test_contract_validation_catches_empty_name():
    from invarium.contracts import AgentContract, validate_contract
    contract = AgentContract(name="")
    errors = validate_contract(contract)
    assert any(e.field == "name" for e in errors)


def test_contract_validation_catches_invalid_step_budget():
    from invarium.contracts import AgentContract, validate_contract
    contract = AgentContract(name="my_agent", step_budget=0)
    errors = validate_contract(contract)
    assert any(e.field == "step_budget" for e in errors)


def test_contract_validation_catches_unknown_scenario_tag():
    from invarium.contracts import AgentContract, validate_contract
    contract = AgentContract(name="my_agent", scenario_tags=["not_a_real_tag"])
    errors = validate_contract(contract)
    assert any(e.field == "scenario_tags" for e in errors)


def test_contract_validation_catches_order_tool_not_in_expected():
    from invarium.contracts import AgentContract, validate_contract
    contract = AgentContract(
        name="my_agent",
        expected_tools=["search"],
        required_tool_order=["search", "ghost_tool"],
    )
    errors = validate_contract(contract)
    assert any(e.field == "required_tool_order" for e in errors)


def test_contract_round_trips_through_json():
    from invarium.contracts import AgentContract, load_contract, save_contract
    contract = AgentContract(
        name="my_agent",
        description="test",
        expected_tools=["search"],
        step_budget=3,
        scenario_tags=["happy_path"],
    )
    path = Path(".build-tmp") / f"contract-{uuid4().hex}.json"
    save_contract(contract, path)
    loaded = load_contract(path)
    assert loaded.name == contract.name
    assert loaded.step_budget == contract.step_budget
    assert loaded.scenario_tags == contract.scenario_tags
