from __future__ import annotations

from invarium.cli import _render_comparison, _render_session_summary_dict


def test_render_session_summary_dict_shows_minimal_structured_output():
    rendered = _render_session_summary_dict(
        {
            "suite_id": "examples",
            "trace_file": ".invarium/traces/latest.json",
            "markdown_report_file": ".invarium/reports/latest.md",
            "reports": [
                {
                    "test_name": "test_booking_agent",
                    "total_runs": 5,
                    "passed_runs": 5,
                    "failed_runs": 0,
                    "success_rate": 100.0,
                    "average_steps": 2.0,
                    "failure_reasons": [],
                    "tool_presence": {
                        "booking_tool": 100.0,
                        "restaurant_search": 100.0,
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
            "baseline_comparison": {
                "summary": "No regression detected across 1 matched test(s).",
                "matched_tests": ["test_booking_agent"],
                "current_only_tests": [],
                "baseline_only_tests": [],
                "regressions": [],
                "suite_mismatch": False,
            },
        }
    )

    assert "Invarium" in rendered
    assert "Suite        examples" in rendered
    assert "Trace        .invarium/traces/latest.json" in rendered
    assert "Markdown     .invarium/reports/latest.md" in rendered
    assert "[PASS] test_booking_agent" in rendered
    assert "Runs         5" in rendered
    assert "Success      100.0%" in rendered
    assert "Tools        booking_tool 100.0%, restaurant_search 100.0%" in rendered
    assert "Path         restaurant_search -> booking_tool (100.0%)" in rendered
    assert "[OK] Baseline comparison" in rendered


def test_render_comparison_shows_regression_details():
    rendered = _render_comparison(
        {
            "summary": "Regression detected in 1 of 1 matched test(s).",
            "matched_tests": ["test_booking_agent"],
            "current_only_tests": [],
            "baseline_only_tests": [],
            "suite_mismatch": False,
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
        }
    )

    assert "[REGRESSION] Baseline comparison" in rendered
    assert "Summary      Regression detected in 1 of 1 matched test(s)." in rendered
    assert "Matched      test_booking_agent" in rendered
    assert "[REGRESSION] test_booking_agent" in rendered
    assert "Success      100.0% -> 60.0%" in rendered
    assert "Step delta   +0.4" in rendered
    assert (
        "Path         restaurant_search -> booking_tool (100.0%) -> restaurant_search (60.0%)"
        in rendered
    )
    assert "Tool drop    booking_tool 100.0% -> 60.0%" in rendered
