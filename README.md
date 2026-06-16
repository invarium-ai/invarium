<div align="center">

<p align="center">
  <img src="assets/invarium-logo.svg" alt="Invarium logo" width="84" height="84" />
</p>

<h1 align="center">Invarium</h1>

**Pytest for AI agents — test behavior, not exact text.**

[![Tests](https://github.com/invarium-ai/invarium/actions/workflows/tests.yml/badge.svg)](https://github.com/invarium-ai/invarium/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/pygent-test.svg)](https://pypi.org/project/pygent-test/)
[![Python versions](https://img.shields.io/pypi/pyversions/pygent-test.svg)](https://pypi.org/project/pygent-test/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Downloads](https://static.pepy.tech/badge/pygent-test/month)](https://pepy.tech/project/pygent-test)
[![Total downloads](https://static.pepy.tech/badge/pygent-test)](https://pepy.tech/project/pygent-test)

[Quickstart](#quickstart) · [Why Invarium](#why-invarium) · [Writing tests](#writing-a-test) · [CLI](#cli-commands) · [Docs](#documentation)

</div>

---

Invarium brings the discipline of unit testing to AI agents. Instead of asserting
on brittle, model-generated text, you assert on **observable behavior** — which tools
an agent called, in what order, how many steps it took, and whether it claimed success
without doing the work. It then tracks that behavior over time and flags regressions
against a saved baseline.

> **Note:** Invarium is distributed on PyPI as the `pygent-test` package and exposes the
> `agentcheck` command-line tool. Use those names when installing and running it.

## Why Invarium

LLM-driven agents are non-deterministic: the same prompt can produce different wording,
different tool paths, and different costs on every run. Traditional string-match tests
break constantly, and pure eval scores tell you *that* something changed but not *what*.

Invarium takes a different approach:

- **Behavioral assertions** — verify tool usage, ordering, step budgets, and success
  claims rather than exact output.
- **Regression detection** — `bless` a baseline, then catch drift in success rate,
  steps, latency, cost, and tool coverage automatically.
- **Flakiness scoring** — run each test multiple times and surface unstable tool paths.
- **Framework-agnostic** — works with OpenAI Agents, LangGraph, CrewAI, plain Python
  callables, or any deployed HTTP endpoint.
- **CI-native** — fail builds on regression and publish reports straight to GitHub
  Actions step summaries.

## Installation

```bash
pip install pygent-test
```

Optional framework adapters:
Optional framework adapters:

```bash
pip install "pygent-test[openai]"      # OpenAI Agents SDK
pip install "pygent-test[langgraph]"   # LangGraph
pip install "pygent-test[crewai]"      # CrewAI
pip install "pygent-test[openai]"      # OpenAI Agents SDK
pip install "pygent-test[langgraph]"   # LangGraph
pip install "pygent-test[crewai]"      # CrewAI
```

Requires Python 3.10+.

Requires Python 3.10+.

## Quickstart
## Quickstart

```bash
pip install -e .
python -m agentcheck.cli test examples            # run example tests
python -m agentcheck.cli bless examples           # save a baseline
python -m agentcheck.cli test regression_examples # catch an intentional regression
```

This walks you through a passing test, a saved baseline, and a regression caught with a
clear behavior diff — in about five minutes.

## Writing a Test
python -m agentcheck.cli test examples            # run example tests
python -m agentcheck.cli bless examples           # save a baseline
python -m agentcheck.cli test regression_examples # catch an intentional regression
```

This walks you through a passing test, a saved baseline, and a regression caught with a
clear behavior diff — in about five minutes.

## Writing a Test

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

`runs=5` executes the test five times so Invarium can measure stability, not just a
single lucky pass.

`runs=5` executes the test five times so Invarium can measure stability, not just a
single lucky pass.

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

Use `collect=True` to gather every failure in one report instead of stopping at the first:
Use `collect=True` to gather every failure in one report instead of stopping at the first:

```python
check = expect(result, collect=True)
check.used_tool("search")
check.steps_less_than(5)
check.verify()
```

### Failure Categories

Every failed assertion is tagged so you know exactly what broke:

| Category | Triggered by |
|---|---|
| `missing_required_tool` | `used_tool`, `used_any_tool`, `used_tool_times`, … |
| `wrong_tool_order` | `used_tools_in_order` |
| `step_budget_exceeded` | `steps_less_than` |
| `unsupported_success_claim` | `did_not_claim_confirmation_without_tool` |
| `runtime_error` | `finished_successfully`, `did_not_error` |
| `output_mismatch` | `final_output_contains`, `final_output_matches_pattern` |
| `tool_failure` | `tool_succeeded` |

### Failure Categories

Every failed assertion is tagged so you know exactly what broke:

| Category | Triggered by |
|---|---|
| `missing_required_tool` | `used_tool`, `used_any_tool`, `used_tool_times`, … |
| `wrong_tool_order` | `used_tools_in_order` |
| `step_budget_exceeded` | `steps_less_than` |
| `unsupported_success_claim` | `did_not_claim_confirmation_without_tool` |
| `runtime_error` | `finished_successfully`, `did_not_error` |
| `output_mismatch` | `final_output_contains`, `final_output_matches_pattern` |
| `tool_failure` | `tool_succeeded` |

## CLI Commands

```bash
# Run tests
agentcheck test [path] [-k filter] [--html report.html] [--fail-on-regression]
agentcheck test [path] [-k filter] [--html report.html] [--fail-on-regression]

# Baselines
agentcheck bless [path]                 # save current run as baseline
agentcheck compare                      # re-compare last run against baseline
# Baselines
agentcheck bless [path]                 # save current run as baseline
agentcheck compare                      # re-compare last run against baseline
agentcheck baseline list
agentcheck baseline inspect .agentcheck/baselines/latest.json
agentcheck baseline delete .agentcheck/baselines/old.json --yes

# Reports
agentcheck report [--html report.html]

# Contracts & scenario generation
# Reports
agentcheck report [--html report.html]

# Contracts & scenario generation
agentcheck contract init my_agent
agentcheck contract validate agent_contract.json
agentcheck generate scenarios agent_contract.json --stub tests/generated_tests.py

# Config & history
# Config & history
agentcheck config init
agentcheck history list
agentcheck history show <run-id>
```

## Adapters

| Adapter | Install | Use with |
|---|---|---|
| `PythonAdapter` | built-in | any Python callable |
| `OpenAIAgentsAdapter` | `pygent-test[openai]` | OpenAI Agents SDK |
| `LangGraphAdapter` | `pygent-test[langgraph]` | LangGraph `StateGraph` |
| `CrewAIAdapter` | `pygent-test[crewai]` | CrewAI Crew / Agent |
| `HttpAdapter` | built-in | any HTTP endpoint |

### Testing a Deployed Agent

Test a live agent over HTTP without importing any local code:

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

Or drive it entirely from environment variables:

```python
adapter = HttpAdapter.from_env(
    url_env_var="AGENT_ENDPOINT",
    auth_env_var="AGENT_API_KEY",
)
```

## Regression Detection

When a baseline exists, `agentcheck test` compares the current run and reports success
rate change, step/latency/cost drift, tool coverage drops, primary tool path changes,
and a failure-category breakdown.
## Adapters

| Adapter | Install | Use with |
|---|---|---|
| `PythonAdapter` | built-in | any Python callable |
| `OpenAIAgentsAdapter` | `pygent-test[openai]` | OpenAI Agents SDK |
| `LangGraphAdapter` | `pygent-test[langgraph]` | LangGraph `StateGraph` |
| `CrewAIAdapter` | `pygent-test[crewai]` | CrewAI Crew / Agent |
| `HttpAdapter` | built-in | any HTTP endpoint |

### Testing a Deployed Agent

Test a live agent over HTTP without importing any local code:

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

Or drive it entirely from environment variables:

```python
adapter = HttpAdapter.from_env(
    url_env_var="AGENT_ENDPOINT",
    auth_env_var="AGENT_API_KEY",
)
```

## Regression Detection

When a baseline exists, `agentcheck test` compares the current run and reports success
rate change, step/latency/cost drift, tool coverage drops, primary tool path changes,
and a failure-category breakdown.

```bash
agentcheck bless examples                          # save a baseline
agentcheck test examples --fail-on-regression      # future runs compare automatically
```
agentcheck bless examples                          # save a baseline
agentcheck test examples --fail-on-regression      # future runs compare automatically
```

## Flakiness Detection

When a test runs multiple times and produces mixed results, Invarium computes a
`flakiness_score` (0–1) and flags `unstable_tool_paths` when tool sequences vary between
runs. Both appear in CLI output and in the HTML/Markdown reports.
When a test runs multiple times and produces mixed results, Invarium computes a
`flakiness_score` (0–1) and flags `unstable_tool_paths` when tool sequences vary between
runs. Both appear in CLI output and in the HTML/Markdown reports.

## Agent Contracts

Define expected behavior once in a reusable file:
Define expected behavior once in a reusable file:

```bash
agentcheck contract init booking_agent
```

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

```bash
agentcheck contract validate agent_contract.json
```

### Scenario Generation
### Scenario Generation

Generate starter test scenarios from a contract:

```bash
agentcheck generate scenarios agent_contract.json --stub tests/generated.py
```

This writes a JSON scenario pack and a ready-to-edit Python test file covering
`happy_path`, `missing_information`, `ambiguous_request`, `tool_failure`, `over_step`,
and `unsupported_success`.

## Reports & Artifacts

Every `agentcheck test` run writes a self-contained HTML report to
`.agentcheck/reports/latest.html` — open it in any browser, no server needed. Use
`--html path` to write it elsewhere.

| File | Contents |
|---|---|
| `.agentcheck/reports/latest.json` | Full session report (JSON) |
| `.agentcheck/reports/latest.md` | Markdown report |
| `.agentcheck/reports/latest.html` | Self-contained HTML report |
| `.agentcheck/traces/latest.json` | Raw per-run traces |
| `.agentcheck/history.json` | Append-only run log (capped at 200 entries) |

## Configuration
This writes a JSON scenario pack and a ready-to-edit Python test file covering
`happy_path`, `missing_information`, `ambiguous_request`, `tool_failure`, `over_step`,
and `unsupported_success`.

## Reports & Artifacts

Every `agentcheck test` run writes a self-contained HTML report to
`.agentcheck/reports/latest.html` — open it in any browser, no server needed. Use
`--html path` to write it elsewhere.

| File | Contents |
|---|---|
| `.agentcheck/reports/latest.json` | Full session report (JSON) |
| `.agentcheck/reports/latest.md` | Markdown report |
| `.agentcheck/reports/latest.html` | Self-contained HTML report |
| `.agentcheck/traces/latest.json` | Raw per-run traces |
| `.agentcheck/history.json` | Append-only run log (capped at 200 entries) |

## Configuration

Create `agentcheck.json` in your project root to set defaults (CLI flags always win):
Create `agentcheck.json` in your project root to set defaults (CLI flags always win):

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

## CI Integration

```yaml
- name: Run Invarium
- name: Run Invarium
  run: agentcheck test . --fail-on-regression --html reports/agentcheck.html

- name: Upload report
  uses: actions/upload-artifact@v4
  with:
    name: invarium-report
    name: invarium-report
    path: reports/agentcheck.html
```

The Markdown report is automatically appended to the GitHub Actions step summary when
`GITHUB_STEP_SUMMARY` is set.
The Markdown report is automatically appended to the GitHub Actions step summary when
`GITHUB_STEP_SUMMARY` is set.

## pytest Integration
## pytest Integration

Invarium tests also run through pytest directly:
Invarium tests also run through pytest directly:

```bash
pytest examples -q
pytest tests -q
```

Filter by name with `-k`:

```bash
agentcheck test -k booking
agentcheck test -k "research or booking"
```
Filter by name with `-k`:

```bash
agentcheck test -k booking
agentcheck test -k "research or booking"
```

## Documentation

- [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) — architecture, adapters, and assertions in depth
- [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) — architecture, adapters, and assertions in depth
- [ADAPTER_GUIDE.md](ADAPTER_GUIDE.md) — how to write a custom adapter
- [REAL_WORLD_TESTING.md](REAL_WORLD_TESTING.md) — live OpenAI agent testing setup
- [ROADMAP.md](ROADMAP.md) — what's done and where the project is going

## Contributing

Contributions are welcome. Please open an issue to discuss substantial changes before
submitting a pull request, and run the test suite first:

```bash
pip install -e ".[dev]"
pytest -q
```

## License

Released under the [MIT License](LICENSE).
- [ROADMAP.md](ROADMAP.md) — what's done and where the project is going

## Contributing

Contributions are welcome. Please open an issue to discuss substantial changes before
submitting a pull request, and run the test suite first:

```bash
pip install -e ".[dev]"
pytest -q
```

## License

Released under the [MIT License](LICENSE).
