from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from invarium import AgentResult, ToolCall, expect


# ── HTML report ─────────────────────────────────────────────────────────────

def test_html_report_is_valid_html():
    from invarium.html_report import render_html_report
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
    assert "Invarium Report" in html
    assert "test_booking" in html
    assert "80.0%" in html
    assert "Regression" in html
    assert "flaky" in html.lower()
    assert "missing_required_tool" in html


def test_html_report_no_comparison():
    from invarium.html_report import render_html_report
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
    from invarium.contracts import AgentContract
    from invarium.scenarios import generate_scenarios

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
    from invarium.contracts import AgentContract
    from invarium.scenarios import generate_scenarios

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
    from invarium.contracts import AgentContract
    from invarium.scenarios import generate_scenarios, render_scenario_stub

    contract = AgentContract(
        name="my_agent",
        expected_tools=["search"],
        step_budget=4,
        scenario_tags=["happy_path"],
    )
    pack = generate_scenarios(contract)
    stub = render_scenario_stub(pack)
    assert "from invarium import" in stub
    assert "@agent_test" in stub
    assert 'check.used_tool("search")' in stub
    assert "check.steps_less_than(4)" in stub


def test_scenario_pack_round_trips_json():
    from invarium.contracts import AgentContract
    from invarium.scenarios import generate_scenarios, load_scenario_pack, save_scenario_pack

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

def _mock_http_response(body: bytes):
    from unittest.mock import MagicMock
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_http_adapter_parses_success_response():
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake-agent.test/run")
    body = b'{"output": "Task done", "tool_calls": [{"name": "search", "args": {}, "success": true}], "steps": 2}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("Find me a restaurant")

    assert result.final_output == "Task done"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search"
    assert result.tool_calls[0].success is True
    assert result.steps == 2
    assert not result.errors


def test_http_adapter_handles_http_error():
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch
    from urllib.error import HTTPError

    adapter = HttpAdapter("http://fake-agent.test/run")
    with patch("invarium.adapters.http.urllib_request.urlopen",
               side_effect=HTTPError("url", 503, "Service Unavailable", {}, None)):
        result = adapter.run_input("query")

    assert result.final_output == ""
    assert any("503" in e for e in result.errors)


def test_http_adapter_handles_url_error():
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch
    from urllib.error import URLError

    adapter = HttpAdapter("http://unreachable.test/run")
    with patch("invarium.adapters.http.urllib_request.urlopen",
               side_effect=URLError("Connection refused")):
        result = adapter.run_input("query")

    assert result.final_output == ""
    assert result.errors
    assert "Connection" in result.errors[0] or "refused" in result.errors[0].lower()


def test_http_adapter_handles_json_parse_error():
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake-agent.test/run")
    with patch("invarium.adapters.http.urllib_request.urlopen",
               return_value=_mock_http_response(b"not valid json {")):
        result = adapter.run_input("query")

    assert result.final_output == ""
    assert result.errors
    assert "JSON" in result.errors[0] or "parse" in result.errors[0].lower()


def test_http_adapter_sets_auth_header(monkeypatch):
    from invarium.adapters.http import HttpAdapter

    monkeypatch.setenv("TEST_API_KEY", "secret-token-123")
    adapter = HttpAdapter("http://agent.test/run", auth_env_var="TEST_API_KEY")
    assert adapter._headers.get("Authorization") == "Bearer secret-token-123"


def test_http_adapter_missing_auth_env_var_does_not_set_header(monkeypatch):
    from invarium.adapters.http import HttpAdapter

    monkeypatch.delenv("ABSENT_KEY", raising=False)
    adapter = HttpAdapter("http://agent.test/run", auth_env_var="ABSENT_KEY")
    assert "Authorization" not in adapter._headers


def test_http_adapter_request_body_uses_custom_key():
    from invarium.adapters.http import HttpAdapter
    import json

    adapter = HttpAdapter("http://fake.test/run", request_key="message")
    parsed = json.loads(adapter._build_body("hello world"))
    assert parsed["message"] == "hello world"
    assert "input" not in parsed


def test_http_adapter_request_extra_merged_into_body():
    from invarium.adapters.http import HttpAdapter
    import json

    adapter = HttpAdapter("http://fake.test/run", request_extra={"model": "gpt-4o", "temperature": 0})
    parsed = json.loads(adapter._build_body("do something"))
    assert parsed["input"] == "do something"
    assert parsed["model"] == "gpt-4o"
    assert parsed["temperature"] == 0


def test_http_adapter_parses_tool_key_alias():
    """'tool' key is accepted as alias for 'name'."""
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake.test/run")
    body = b'{"output": "done", "tool_calls": [{"tool": "search", "arguments": {"q": "test"}, "ok": true}]}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert result.tool_calls[0].name == "search"
    assert result.tool_calls[0].args == {"q": "test"}
    assert result.tool_calls[0].success is True


def test_http_adapter_parses_input_key_alias():
    """'input' key is accepted as alias for 'args'."""
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake.test/run")
    body = b'{"output": "done", "tool_calls": [{"name": "fetch", "input": {"url": "http://x"}}]}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert result.tool_calls[0].args == {"url": "http://x"}


def test_http_adapter_parses_result_key_alias():
    """'result' key is accepted as alias for 'output'."""
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake.test/run")
    body = b'{"output": "done", "tool_calls": [{"name": "fetch", "result": "page content"}]}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert result.tool_calls[0].output == "page content"


def test_http_adapter_parses_string_tool_calls():
    """Tool calls array may contain plain strings (just tool names)."""
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake.test/run")
    body = b'{"output": "done", "tool_calls": ["search", "book"]}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert [t.name for t in result.tool_calls] == ["search", "book"]


def test_http_adapter_empty_tool_calls_list():
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake.test/run")
    body = b'{"output": "done", "tool_calls": []}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert result.tool_calls == []


def test_http_adapter_tools_key_none_disables_parsing():
    """response_tools_key=None means tool_calls are never read from the response."""
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake.test/run", response_tools_key=None)
    body = b'{"output": "done", "tool_calls": [{"name": "search"}]}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert result.tool_calls == []


def test_http_adapter_uses_reported_latency_from_response():
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake.test/run")
    body = b'{"output": "done", "latency": 0.42}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert result.latency == pytest.approx(0.42)


def test_http_adapter_uses_reported_cost_from_response():
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake.test/run")
    body = b'{"output": "done", "cost": 0.0015}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert result.cost == pytest.approx(0.0015)


def test_http_adapter_steps_fallback_to_tool_count():
    """When 'steps' key is absent, steps = len(tool_calls)."""
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake.test/run")
    body = b'{"output": "done", "tool_calls": [{"name": "a"}, {"name": "b"}]}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert result.steps == 2


def test_http_adapter_custom_response_output_key():
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://fake.test/run", response_output_key="answer")
    body = b'{"answer": "42", "output": "ignored"}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert result.final_output == "42"


def test_http_adapter_metadata_contains_url():
    from invarium.adapters.http import HttpAdapter
    from unittest.mock import patch

    adapter = HttpAdapter("http://my-agent.test/run")
    body = b'{"output": "done"}'
    with patch("invarium.adapters.http.urllib_request.urlopen", return_value=_mock_http_response(body)):
        result = adapter.run_input("query")

    assert result.metadata.get("http_url") == "http://my-agent.test/run"


def test_http_adapter_from_env(monkeypatch):
    from invarium.adapters.http import HttpAdapter

    monkeypatch.setenv("MY_AGENT_URL", "http://agent.test/run")
    adapter = HttpAdapter.from_env(url_env_var="MY_AGENT_URL", auth_env_var=None)
    assert adapter.url == "http://agent.test/run"


def test_http_adapter_from_env_missing_url(monkeypatch):
    from invarium.adapters.http import HttpAdapter

    monkeypatch.delenv("MISSING_URL_VAR", raising=False)
    with pytest.raises(ValueError, match="MISSING_URL_VAR"):
        HttpAdapter.from_env(url_env_var="MISSING_URL_VAR", auth_env_var=None)


# ── CrewAI adapter ───────────────────────────────────────────────────────────

def test_crewai_adapter_normalize_string_output():
    from invarium.adapters.crewai import CrewAIAdapter

    adapter = CrewAIAdapter()
    result = adapter.normalize("What is AI?", "AI stands for Artificial Intelligence.")
    assert result.final_output == "AI stands for Artificial Intelligence."
    assert result.steps >= 1


def test_crewai_adapter_normalize_crew_result_object():
    from invarium.adapters.crewai import CrewAIAdapter

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


def test_crewai_adapter_normalize_dict_output():
    from invarium.adapters.crewai import CrewAIAdapter

    adapter = CrewAIAdapter()
    result = adapter.normalize("q", {"output": "result text"})
    assert result.final_output == "result text"


def test_crewai_adapter_normalize_unknown_type_falls_back_to_str():
    from invarium.adapters.crewai import CrewAIAdapter

    adapter = CrewAIAdapter()
    result = adapter.normalize("q", 42)
    assert result.final_output == "42"


def test_crewai_adapter_extract_errors_list():
    from invarium.adapters.crewai import CrewAIAdapter

    adapter = CrewAIAdapter()
    result = adapter.normalize("q", {"errors": ["tool failed", "timeout"]})
    assert "tool failed" in result.errors
    assert "timeout" in result.errors


def test_crewai_adapter_extract_errors_string():
    from invarium.adapters.crewai import CrewAIAdapter

    adapter = CrewAIAdapter()
    result = adapter.normalize("q", {"error": "something went wrong"})
    assert result.errors == ["something went wrong"]


def test_crewai_adapter_extract_cost_from_token_usage():
    from invarium.adapters.crewai import CrewAIAdapter

    class FakeUsage:
        total_cost = 0.0023

    class FakeResult:
        raw = "answer"
        tasks_output = None
        token_usage = FakeUsage()
        error = None

    adapter = CrewAIAdapter()
    result = adapter.normalize("q", FakeResult())
    assert result.cost == pytest.approx(0.0023)


def test_crewai_adapter_no_cost_when_no_usage():
    from invarium.adapters.crewai import CrewAIAdapter

    adapter = CrewAIAdapter()
    result = adapter.normalize("q", "plain answer")
    assert result.cost is None


def test_crewai_adapter_tasks_output_dict_items():
    """tasks_output as a list of dicts — both success and error cases."""
    from invarium.adapters.crewai import CrewAIAdapter

    adapter = CrewAIAdapter()
    result = adapter.normalize("q", {
        "raw": "done",
        "tasks_output": [
            {"name": "task_a", "raw": "out_a", "error": None},
            {"name": "task_b", "raw": "out_b", "error": "oops"},
        ],
    })
    assert len(result.tool_calls) == 2
    assert result.tool_calls[0].name == "task_a"
    assert result.tool_calls[0].success is True
    assert result.tool_calls[1].name == "task_b"
    assert result.tool_calls[1].success is False


def test_crewai_adapter_tasks_output_single_object():
    """tasks_output as a single non-list object is still wrapped into one ToolCall."""
    from invarium.adapters.crewai import CrewAIAdapter

    adapter = CrewAIAdapter()
    result = adapter.normalize("q", {
        "raw": "done",
        "tasks_output": {"name": "solo_task", "raw": "output", "error": None},
    })
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "solo_task"


def test_crewai_adapter_run_calls_kickoff(monkeypatch):
    """run() calls crew.kickoff() with all prompt aliases and returns normalized result."""
    import sys
    from unittest.mock import MagicMock
    from invarium.adapters.crewai import CrewAIAdapter

    monkeypatch.setitem(sys.modules, "crewai", MagicMock())

    fake_crew = MagicMock()
    fake_crew.kickoff.return_value = "Task complete"

    adapter = CrewAIAdapter()
    result = adapter.run(fake_crew, "run the crew")

    fake_crew.kickoff.assert_called_once_with(
        inputs={"input": "run the crew", "prompt": "run the crew", "query": "run the crew"}
    )
    assert result.final_output == "Task complete"
    assert not result.errors


def test_crewai_adapter_run_handles_kickoff_exception(monkeypatch):
    """Exceptions from kickoff() are caught and surfaced as errors on AgentResult."""
    import sys
    from unittest.mock import MagicMock
    from invarium.adapters.crewai import CrewAIAdapter

    monkeypatch.setitem(sys.modules, "crewai", MagicMock())

    fake_crew = MagicMock()
    fake_crew.kickoff.side_effect = RuntimeError("crew failed")

    adapter = CrewAIAdapter()
    result = adapter.run(fake_crew, "run")

    assert result.final_output == ""
    assert any("crew failed" in e for e in result.errors)
    assert result.metadata.get("exception_type") == "RuntimeError"


def test_crewai_adapter_run_agent_calls_execute_task(monkeypatch):
    """run_agent() creates a Task and calls agent.execute_task()."""
    import sys
    from unittest.mock import MagicMock
    from invarium.adapters.crewai import CrewAIAdapter

    fake_crewai = MagicMock()
    fake_task_instance = MagicMock()
    fake_crewai.Task.return_value = fake_task_instance
    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)

    fake_agent = MagicMock()
    fake_agent.execute_task.return_value = "agent output"

    adapter = CrewAIAdapter()
    result = adapter.run_agent(fake_agent, "do the task")

    fake_agent.execute_task.assert_called_once_with(fake_task_instance)
    assert result.final_output == "agent output"


def test_crewai_adapter_run_agent_handles_exception(monkeypatch):
    """Exceptions from execute_task() are caught and surfaced as errors."""
    import sys
    from unittest.mock import MagicMock
    from invarium.adapters.crewai import CrewAIAdapter

    fake_crewai = MagicMock()
    fake_crewai.Task.return_value = MagicMock()
    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)

    fake_agent = MagicMock()
    fake_agent.execute_task.side_effect = ValueError("agent exploded")

    adapter = CrewAIAdapter()
    result = adapter.run_agent(fake_agent, "do the task")

    assert result.final_output == ""
    assert any("agent exploded" in e for e in result.errors)
    assert result.metadata.get("exception_type") == "ValueError"


def test_crewai_adapter_import_guard_raises(monkeypatch):
    """ImportError is raised with a helpful message when crewai is not installed."""
    import sys
    from unittest.mock import MagicMock
    from invarium.adapters.crewai import CrewAIAdapter

    # sys.modules[key] = None causes 'import crewai' to raise ImportError
    monkeypatch.setitem(sys.modules, "crewai", None)

    adapter = CrewAIAdapter()
    with pytest.raises(ImportError, match="crewai"):
        adapter.run(MagicMock(), "test")


# ── Run history ──────────────────────────────────────────────────────────────

def test_history_record_and_retrieve(monkeypatch):
    from invarium import history as history_mod
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
    from invarium import history as history_mod
    tmp_file = Path(".build-tmp") / f"history-{uuid4().hex}.json"
    monkeypatch.setattr(history_mod, "HISTORY_FILE", tmp_file)

    reports = [{"test_name": "t1", "failed_runs": 0, "success_rate": 100.0, "average_steps": 1.0, "flakiness_score": 0.0}]
    entry = history_mod.record_run(reports, None, has_regression=False)
    found = history_mod.get_entry(entry.run_id[:6])
    assert found is not None
    assert found.run_id == entry.run_id


def test_history_list_is_most_recent_first(monkeypatch):
    from invarium import history as history_mod
    tmp_file = Path(".build-tmp") / f"history-{uuid4().hex}.json"
    monkeypatch.setattr(history_mod, "HISTORY_FILE", tmp_file)

    reports = [{"test_name": "t", "failed_runs": 0, "success_rate": 100.0, "average_steps": 1.0, "flakiness_score": 0.0}]
    e1 = history_mod.record_run(reports, None, has_regression=False)
    e2 = history_mod.record_run(reports, None, has_regression=False)

    listing = history_mod.get_history(10)
    assert listing[0].run_id == e2.run_id
    assert listing[1].run_id == e1.run_id
