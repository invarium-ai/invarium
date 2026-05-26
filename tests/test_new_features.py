from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agentcheck import AgentResult, ToolCall, expect


# ── HTML report ─────────────────────────────────────────────────────────────

def test_html_report_is_valid_html():
    from agentcheck.html_report import render_html_report
    session = {
        "created_at": "2026-05-26T00:00:00Z",
        "suite_id": "examples",
        "reports": [
            {
                "test_name": "test_booking",
                "total_runs": 5,
                "passed_runs": 4,
                "failed_runs": 1,
                "success_rate": 80.0,
                "average_steps": 2.5,
                "failure_reasons": ["Expected tool `book` to be called."],
                "failure_categories": {"missing_required_tool": 1},
                "flakiness_score": 0.16,
                "unstable_tool_paths": True,
                "tool_presence": {"search": 100.0, "book": 80.0},
                "common_tool_paths": [{"path": ["search", "book"], "count": 4, "rate": 80.0}],
                "average_latency": 1.23,
                "average_cost": 0.002,
            }
        ],
        "baseline_comparison": {
            "summary": "Regression detected in 1 of 1 matched test(s).",
            "matched_tests": ["test_booking"],
            "current_only_tests": [],
            "baseline_only_tests": [],
            "regressions": [
                {
                    "test_name": "test_booking",
                    "previous_success_rate": 100.0,
                    "current_success_rate": 80.0,
                    "step_delta": 0.5,
                    "latency_delta": 0.3,
                    "cost_delta": 0.001,
                    "failure_categories": {"missing_required_tool": 1},
                    "primary_path_change": None,
                    "tool_coverage_drops": [],
                }
            ],
        },
    }
    html = render_html_report(session)
    assert "<!doctype html>" in html.lower()
    assert "AgentCheck Report" in html
    assert "test_booking" in html
    assert "80.0%" in html
    assert "Regression" in html
    assert "flaky" in html.lower()
    assert "missing_required_tool" in html


def test_html_report_no_comparison():
    from agentcheck.html_report import render_html_report
    html = render_html_report({
        "created_at": "2026-05-26T00:00:00Z",
        "reports": [
            {
                "test_name": "test_clean",
                "total_runs": 3,
                "passed_runs": 3,
                "failed_runs": 0,
                "success_rate": 100.0,
                "average_steps": 1.0,
                "failure_reasons": [],
                "tool_presence": {},
                "common_tool_paths": [],
            }
        ],
    })
    assert "test_clean" in html
    assert "100" in html


# ── Scenario generation ──────────────────────────────────────────────────────

def test_generate_scenarios_from_contract():
    from agentcheck.contracts import AgentContract
    from agentcheck.scenarios import generate_scenarios

    contract = AgentContract(
        name="booking_agent",
        expected_tools=["search", "book"],
        step_budget=5,
        forbidden_claims=["confirmed"],
        scenario_tags=["happy_path", "tool_failure"],
    )
    pack = generate_scenarios(contract)
    assert pack.contract_name == "booking_agent"
    assert len(pack.scenarios) == 2
    names = [s.name for s in pack.scenarios]
    assert "test_booking_agent_happy_path" in names
    assert "test_booking_agent_tool_failure" in names


def test_scenario_happy_path_includes_all_expected_tools():
    from agentcheck.contracts import AgentContract
    from agentcheck.scenarios import generate_scenarios

    contract = AgentContract(
        name="my_agent",
        expected_tools=["fetch", "summarize"],
        scenario_tags=["happy_path"],
    )
    pack = generate_scenarios(contract)
    happy = next(s for s in pack.scenarios if s.category == "happy_path")
    assert "fetch" in happy.expected_tools
    assert "summarize" in happy.expected_tools


def test_generate_scenario_stub_is_valid_python():
    from agentcheck.contracts import AgentContract
    from agentcheck.scenarios import generate_scenarios, render_scenario_stub

    contract = AgentContract(
        name="my_agent",
        expected_tools=["search"],
        step_budget=4,
        scenario_tags=["happy_path"],
    )
    pack = generate_scenarios(contract)
    stub = render_scenario_stub(pack)
    assert "from agentcheck import" in stub
    assert "@agent_test" in stub
    assert 'check.used_tool("search")' in stub
    assert "check.steps_less_than(4)" in stub


def test_scenario_pack_round_trips_json():
    from agentcheck.contracts import AgentContract
    from agentcheck.scenarios import generate_scenarios, load_scenario_pack, save_scenario_pack

    contract = AgentContract(
        name="trip_agent",
        expected_tools=["search"],
        scenario_tags=["happy_path"],
    )
    pack = generate_scenarios(contract)
    path = Path(".build-tmp") / f"scenarios-{uuid4().hex}.json"
    save_scenario_pack(pack, path)
    loaded = load_scenario_pack(path)
    assert loaded.contract_name == pack.contract_name
    assert len(loaded.scenarios) == len(pack.scenarios)


# ── HTTP adapter ─────────────────────────────────────────────────────────────

def test_http_adapter_parses_success_response():
    from agentcheck.adapters.http import HttpAdapter
    from unittest.mock import patch, MagicMock
    import io

    adapter = HttpAdapter("http://fake-agent.test/run")
    response_body = b'{"output": "Task done", "tool_calls": [{"name": "search", "args": {}, "success": true}], "steps": 2}'

    mock_resp = MagicMock()
    mock_resp.read.return_value = response_body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("agentcheck.adapters.http.urllib_request.urlopen", return_value=mock_resp):
        result = adapter.run_input("Find me a restaurant")

    assert result.final_output == "Task done"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search"
    assert result.tool_calls[0].success is True
    assert result.steps == 2
    assert not result.errors


def test_http_adapter_handles_http_error():
    from agentcheck.adapters.http import HttpAdapter
    from unittest.mock import patch
    from urllib.error import HTTPError

    adapter = HttpAdapter("http://fake-agent.test/run")
    with patch("agentcheck.adapters.http.urllib_request.urlopen", side_effect=HTTPError("url", 503, "Service Unavailable", {}, None)):
        result = adapter.run_input("query")

    assert result.final_output == ""
    assert any("503" in e for e in result.errors)


def test_http_adapter_from_env(monkeypatch):
    from agentcheck.adapters.http import HttpAdapter
    monkeypatch.setenv("MY_AGENT_URL", "http://agent.test/run")
    adapter = HttpAdapter.from_env(url_env_var="MY_AGENT_URL", auth_env_var=None)
    assert adapter.url == "http://agent.test/run"


def test_http_adapter_from_env_missing_url(monkeypatch):
    from agentcheck.adapters.http import HttpAdapter
    import pytest
    monkeypatch.delenv("MISSING_URL_VAR", raising=False)
    with pytest.raises(ValueError, match="MISSING_URL_VAR"):
        HttpAdapter.from_env(url_env_var="MISSING_URL_VAR", auth_env_var=None)


# ── CrewAI adapter ───────────────────────────────────────────────────────────

def test_crewai_adapter_normalize_string_output():
    from agentcheck.adapters.crewai import CrewAIAdapter
    adapter = CrewAIAdapter()
    result = adapter.normalize("What is AI?", "AI stands for Artificial Intelligence.")
    assert result.final_output == "AI stands for Artificial Intelligence."
    assert result.steps >= 1


def test_crewai_adapter_normalize_crew_result_object():
    from agentcheck.adapters.crewai import CrewAIAdapter

    class FakeCrew:
        raw = "Final answer here"
        tasks_output = [
            type("T", (), {"name": "research_task", "raw": "done", "error": None})()
        ]
        token_usage = None

    adapter = CrewAIAdapter()
    result = adapter.normalize("query", FakeCrew())
    assert result.final_output == "Final answer here"
    assert result.tool_calls[0].name == "research_task"


# ── Run history ──────────────────────────────────────────────────────────────

def test_history_record_and_retrieve(monkeypatch):
    from agentcheck import history as history_mod
    tmp_file = Path(".build-tmp") / f"history-{uuid4().hex}.json"
    monkeypatch.setattr(history_mod, "HISTORY_FILE", tmp_file)

    reports = [
        {"test_name": "t1", "failed_runs": 0, "success_rate": 100.0, "average_steps": 2.0, "flakiness_score": 0.0},
        {"test_name": "t2", "failed_runs": 1, "success_rate": 50.0, "average_steps": 3.0, "flakiness_score": 0.25},
    ]
    entry = history_mod.record_run(reports, "suite_x", has_regression=False)
    assert entry.total_tests == 2
    assert entry.passed_tests == 1
    assert entry.failed_tests == 1
    assert entry.has_regression is False

    found = history_mod.get_entry(entry.run_id)
    assert found is not None
    assert found.run_id == entry.run_id
    assert len(found.tests) == 2


def test_history_prefix_lookup(monkeypatch):
    from agentcheck import history as history_mod
    tmp_file = Path(".build-tmp") / f"history-{uuid4().hex}.json"
    monkeypatch.setattr(history_mod, "HISTORY_FILE", tmp_file)

    reports = [{"test_name": "t1", "failed_runs": 0, "success_rate": 100.0, "average_steps": 1.0, "flakiness_score": 0.0}]
    entry = history_mod.record_run(reports, None, has_regression=False)
    found = history_mod.get_entry(entry.run_id[:6])
    assert found is not None
    assert found.run_id == entry.run_id


def test_history_list_is_most_recent_first(monkeypatch):
    from agentcheck import history as history_mod
    tmp_file = Path(".build-tmp") / f"history-{uuid4().hex}.json"
    monkeypatch.setattr(history_mod, "HISTORY_FILE", tmp_file)

    reports = [{"test_name": "t", "failed_runs": 0, "success_rate": 100.0, "average_steps": 1.0, "flakiness_score": 0.0}]
    e1 = history_mod.record_run(reports, None, has_regression=False)
    e2 = history_mod.record_run(reports, None, has_regression=False)

    listing = history_mod.get_history(10)
    assert listing[0].run_id == e2.run_id
    assert listing[1].run_id == e1.run_id
