# AgentCheck

AgentCheck is pytest for AI agents. Test behavior, not exact text.

- GitHub: `https://github.com/ashutosh-rath02/pygent-test/`
- PyPI: `https://pypi.org/project/pygent-test/`

## Install

```bash
pip install pygent-test
```

Optional framework extras:

```bash
pip install "pygent-test[openai]"
pip install "pygent-test[langgraph]"
pip install "pygent-test[crewai]"
```

## Quickstart (5 minutes)

```bash
pip install -e .
python -m agentcheck.cli test examples
python -m agentcheck.cli bless examples
python -m agentcheck.cli test regression_examples
```

This shows a passing test, a baseline being saved, and an intentional regression caught with a clear behavior diff.

## What It Tests

AgentCheck checks observable agent behavior:

- which tools were called, and how many times
- whether tools ran in the expected order
- whether the agent stayed within a step budget
- whether the agent claimed success without tool evidence
- whether any of the above regressed against a saved baseline
- whether output matched or avoided specific content or patterns

## Write a Test

```python
from agentcheck import agent_test, expect

@agent_test(runs=5, agent_factory=MyAgent)
def test_booking_agent(agent):
    result = agent.run("Book a table for 2 tonight")

    check = expect(result, collect=True)
    check.used_tool("restaurant_search")
    check.used_tool("booking_tool")
    check.steps_less_than(5)
    check.did_not_claim_confirmation_without_tool("booking_tool")
    check.verify()
    return result
```

## Assertions

```python
expect(result).used_tool("search")
expect(result).used_tool_times("search", 2)
expect(result).used_tool_at_least("search", 1)
expect(result).used_tool_at_most("search", 3)
expect(result).did_not_use_tool("forbidden_tool")
expect(result).used_tools_in_order(["search", "summarize"])
expect(result).used_any_tool()
expect(result).tool_succeeded("book")
expect(result).steps_less_than(10)
expect(result).finished_successfully()
expect(result).did_not_error()
expect(result).final_output_contains("confirmed")
expect(result).final_output_does_not_contain("error")
expect(result).final_output_matches_pattern(r"Order #\d+")
expect(result).did_not_claim_confirmation_without_tool("booking_tool")
```

Chain multiple checks with `collect=True` to get all failures at once:

```python
check = expect(result, collect=True)
check.used_tool("search")
check.steps_less_than(5)
check.verify()
```

## CLI Commands

```bash
# Run tests
agentcheck test [path] [-k filter_pattern] [--html report.html] [--fail-on-regression]

# Save baseline
agentcheck bless [path]

# Re-compare last run against baseline
agentcheck compare

# Print last report
agentcheck report [--html report.html]

# Baseline management
agentcheck baseline list
agentcheck baseline inspect .agentcheck/baselines/latest.json
agentcheck baseline delete .agentcheck/baselines/old.json --yes

# Agent contracts
agentcheck contract init my_agent
agentcheck contract validate agent_contract.json

# Scenario generation
agentcheck generate scenarios agent_contract.json --stub tests/generated_tests.py

# Config file
agentcheck config init

# Run history
agentcheck history list
agentcheck history show <run-id>
```

## HTML Report

Every `agentcheck test` run automatically writes a self-contained HTML report to `.agentcheck/reports/latest.html`. Open it in any browser — no server needed.

To write it to a custom path:

```bash
agentcheck test examples --html reports/run.html
```

## Failure Categories

Every failed assertion is labeled with a category so you know exactly what type of failure occurred:

| Category | Triggered by |
|---|---|
| `missing_required_tool` | `used_tool`, `used_any_tool`, `used_tool_times`, etc. |
| `wrong_tool_order` | `used_tools_in_order` |
| `step_budget_exceeded` | `steps_less_than` |
| `unsupported_success_claim` | `did_not_claim_confirmation_without_tool` |
| `runtime_error` | `finished_successfully`, `did_not_error` |
| `output_mismatch` | `final_output_contains`, `final_output_matches_pattern` |
| `tool_failure` | `tool_succeeded` |

## Flakiness Detection

When a test runs multiple times and produces mixed results, AgentCheck computes a `flakiness_score` (0–1) and flags `unstable_tool_paths` when tool sequences vary between runs. Both appear in CLI output and the HTML/Markdown reports.

## Agent Contracts

Define expected agent behavior in a reusable file:

```bash
agentcheck contract init booking_agent
```

This creates `agent_contract.json`:

```json
{
  "name": "booking_agent",
  "expected_tools": ["search", "summarize"],
  "required_tool_order": [],
  "step_budget": 10,
  "success_conditions": ["answer provided"],
  "forbidden_claims": ["reservation complete"],
  "scenario_tags": ["happy_path"]
}
```

Validate it:

```bash
agentcheck contract validate agent_contract.json
```

## Scenario Generation

Generate starter test scenarios from a contract:

```bash
agentcheck generate scenarios agent_contract.json --stub tests/generated.py
```

This writes a JSON scenario pack and a ready-to-edit Python test file covering:
`happy_path`, `missing_information`, `ambiguous_request`, `tool_failure`, `over_step`, `unsupported_success`

## HTTP Endpoint Testing

Test a deployed agent without importing any local code:

```python
from agentcheck import agent_test, expect, HttpAdapter

adapter = HttpAdapter(
    "https://my-agent.example.com/run",
    auth_env_var="AGENT_API_KEY",
)

@agent_test(runs=3)
def test_deployed_agent():
    result = adapter.run_input("What is the weather in Tokyo?")
    return expect(result).used_any_tool().finished_successfully().verify()
```

Or fully environment-driven:

```python
adapter = HttpAdapter.from_env(
    url_env_var="AGENT_ENDPOINT",
    auth_env_var="AGENT_API_KEY",
)
```

## Config File

Create `agentcheck.json` in your project root to set defaults:

```bash
agentcheck config init
```

```json
{
  "path": ".",
  "runs": 3,
  "fail_on_regression": false
}
```

CLI flags always override config file values.

## Run History

Every test run is automatically recorded locally:

```bash
agentcheck history list
agentcheck history show abc123
```

History is stored at `.agentcheck/history.json` and capped at 200 entries.

## Adapters

| Adapter | Install | Usage |
|---|---|---|
| `PythonAdapter` | built-in | any Python callable |
| `OpenAIAgentsAdapter` | `pygent-test[openai]` | OpenAI Agents SDK |
| `LangGraphAdapter` | `pygent-test[langgraph]` | LangGraph `StateGraph` |
| `CrewAIAdapter` | `pygent-test[crewai]` | CrewAI Crew / Agent |
| `HttpAdapter` | built-in | any HTTP endpoint |

## Regression Detection

When a baseline exists, `agentcheck test` compares the current run and reports:

- success rate change per test
- step drift, latency drift, cost drift
- tool coverage drops
- primary tool path changes
- failure category breakdown

```bash
# Save a baseline
agentcheck bless examples

# Future runs compare automatically
agentcheck test examples --fail-on-regression
```

## Test Filtering

Run a subset of tests by name:

```bash
agentcheck test -k booking
agentcheck test -k "research or booking"
```

## CI Integration

```yaml
- name: Run AgentCheck
  run: agentcheck test . --fail-on-regression --html reports/agentcheck.html

- name: Upload report
  uses: actions/upload-artifact@v4
  with:
    name: agentcheck-report
    path: reports/agentcheck.html
```

The Markdown report is automatically written to the GitHub Actions step summary when `GITHUB_STEP_SUMMARY` is set.

## pytest

AgentCheck tests also run through pytest:

```bash
pytest examples -q
pytest tests -q
```

## Artifacts Written Per Run

| File | Contents |
|---|---|
| `.agentcheck/reports/latest.json` | Full session report (JSON) |
| `.agentcheck/reports/latest.md` | Markdown report |
| `.agentcheck/reports/latest.html` | Self-contained HTML report |
| `.agentcheck/traces/latest.json` | Raw per-run traces |
| `.agentcheck/history.json` | Append-only run log |

## Documentation

- [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) — architecture, adapters, assertions in depth
- [ADAPTER_GUIDE.md](ADAPTER_GUIDE.md) — how to write a custom adapter
- [REAL_WORLD_TESTING.md](REAL_WORLD_TESTING.md) — live OpenAI agent testing setup
- [ROADMAP.md](ROADMAP.md) — what is done and where the project is going
