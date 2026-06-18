# Invarium Roadmap

The goal is to make agent behavior testing simple, useful, and repeatable.

## Guiding Principle

Invarium should help developers answer:

- did the agent behave correctly?
- did that behavior regress?
- what specifically broke?

## Done

Everything below is shipped and available in the current package.

### Core test model
- repeated-run behavioral tests with `@agent_test(..., runs=N)`
- normalized `AgentResult` and `ToolCall` models
- collected assertion mode with `verify()`
- local traces, JSON reports, and baselines
- automatic Markdown and HTML report generation
- suite-specific baseline isolation
- regression detection with behavior diffs

### Assertions
- `used_tool(name)`
- `used_tool_times(name, count)`
- `used_tool_at_least(name, count)`
- `used_tool_at_most(name, count)`
- `did_not_use_tool(name)`
- `used_tools_in_order([...])`
- `steps_less_than(n)`
- `finished_successfully()`
- `did_not_error()`
- `final_output_contains(text)`
- `final_output_does_not_contain(text)`
- `did_not_claim_confirmation_without_tool(name)`
- `used_any_tool()`
- `final_output_matches_pattern(regex)`
- `tool_succeeded(name)`

### Failure taxonomy
- every assertion failure carries a structured category:
  `missing_required_tool`, `wrong_tool_order`, `step_budget_exceeded`,
  `unsupported_success_claim`, `runtime_error`, `output_mismatch`, `tool_failure`
- failure categories aggregated per test in reports

### Regression analysis
- tool coverage drops between current and baseline
- primary tool path changes
- step drift, latency drift, cost drift
- failure category breakdown per regression

### Flakiness detection
- `flakiness_score` per test (variance-based, 0–1)
- `unstable_tool_paths` flag when tool sequences vary across runs
- shown in CLI output, Markdown report, and HTML report

### CLI commands
- `invarium test [path] [-k filter] [--html out.html] [--fail-on-regression]`
- `invarium bless [path]`
- `invarium compare`
- `invarium report [--html out.html]`
- `invarium baseline list`
- `invarium baseline inspect <path>`
- `invarium baseline delete <path> [--yes]`
- `invarium contract init [name] [--output]`
- `invarium contract validate [path]`
- `invarium generate scenarios <contract> [--output] [--stub]`
- `invarium config init [--output]`
- `invarium history list [--limit N]`
- `invarium history show <run-id>`

### Agent contracts
- JSON contract schema: expected tools, required order, step budget, success conditions, forbidden claims, scenario tags
- `validate_contract()` with field-level error messages
- `invarium contract init` and `invarium contract validate`

### Scenario generation
- `generate_scenarios()` builds a scenario pack from a contract across 6 categories
- `render_scenario_stub()` emits a ready-to-edit Python test file
- `invarium generate scenarios`

### Config file
- `invarium.json` at project root sets default runs, path, filter, fail-on-regression
- `invarium config init` scaffolds the file

### Run history
- append-only local history log at `.invarium/history.json`
- auto-recorded after every `invarium test` run
- `invarium history list` and `history show <run-id>` with prefix lookup

### Adapters
- plain Python adapter (`PythonAdapter`)
- OpenAI Agents SDK adapter (`OpenAIAgentsAdapter`)
- LangGraph adapter (`LangGraphAdapter`)
- CrewAI adapter (`CrewAIAdapter`)
- HTTP endpoint adapter (`HttpAdapter`) for deployed agents

### Developer experience
- pytest integration via `pytest11` entry point
- test filtering with `--filter` / `-k`
- GitHub Actions step summary support
- smoke-test script

## Not Planned

To stay focused, Invarium explicitly avoids:

- building a dashboard-first product
- fuzzy LLM-as-judge scoring
- benchmark platform features
- niche assertions that only fit one team
- heavy hosted infrastructure before the local product loop is proven

## Contributor-Friendly Areas

Good places to contribute:

- new adapters (smolagents, AutoGen, Pydantic AI, etc.)
- better examples for each adapter
- more broadly reusable assertions
- documentation improvements
