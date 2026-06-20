#!/usr/bin/env bash
#
# Second batch of good-first-issue / help-wanted issues for invarium-ai/invarium.
#
# Usage:
#   GH_TOKEN=ghp_yourtoken bash scripts/seed-issues-2.sh
#
# The token must belong to an account with write access to the repo
# (a classic PAT with the `repo` scope, or a fine-grained PAT with
# Issues: Read and write). Nothing is stored; the token is only used
# for these API calls.
#
# Re-running this script creates DUPLICATE issues. Run it once.

set -euo pipefail

REPO="invarium-ai/invarium"
API="https://api.github.com/repos/${REPO}/issues"

: "${GH_TOKEN:?Set GH_TOKEN to a GitHub token with repo/issues write access}"

# Find a usable JSON builder: jq, or any Python interpreter (incl. the venv).
PY=""
if ! command -v jq >/dev/null 2>&1; then
  for c in python3 python py ./venv/Scripts/python.exe ./venv/bin/python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
  done
  if [ -z "$PY" ]; then
    echo "ERROR: need either jq or a python interpreter to build JSON." >&2
    exit 1
  fi
fi

create_issue() {
  local title="$1"
  local body="$2"
  local labels="$3"  # JSON array string, e.g. ["good first issue"]

  if command -v jq >/dev/null 2>&1; then
    payload=$(jq -n --arg t "$title" --arg b "$body" --argjson l "$labels" \
      '{title:$t, body:$b, labels:$l}')
  else
    payload=$(printf '{"title":%s,"body":%s,"labels":%s}' \
      "$(printf '%s' "$title" | "$PY" -c 'import json,sys;print(json.dumps(sys.stdin.read()))')" \
      "$(printf '%s' "$body"  | "$PY" -c 'import json,sys;print(json.dumps(sys.stdin.read()))')" \
      "$labels")
  fi

  echo "Creating: $title"
  curl -sS -X POST "$API" \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    -d "$payload" \
    | { command -v jq >/dev/null 2>&1 && jq -r '"  -> #\(.number) \(.html_url)"' || cat; }
  sleep 1
}

create_issue \
"Add an invarium --version flag" \
'The CLI (\`invarium\`, defined in \`invarium/cli.py\`) has no way to print the installed version.

### Task
Add a top-level \`--version\` flag that prints the installed \`invarium\` version and exits, e.g.:
\`\`\`
$ invarium --version
invarium 0.3.1
\`\`\`

### Hints
- Read the version with \`importlib.metadata.version("invarium")\`.
- If you use argparse, \`action="version"\` is the simplest wiring.

### Acceptance criteria
- [ ] \`invarium --version\` prints the version and exits 0
- [ ] A short note in the README CLI section
- [ ] A unit test under \`tests/\`' \
'["good first issue","enhancement"]'

create_issue \
"Use a forbidden_tool_used failure category for did_not_use_tool" \
'\`did_not_use_tool(name)\` in \`invarium/assertions.py\` fails with category \`missing_required_tool\`, but the failure is the opposite: a tool that should have been avoided **was** used. The category is misleading in reports.

### Task
- Add a \`forbidden_tool_used\` entry to \`FAILURE_CATEGORIES\`.
- Use it as the category for \`did_not_use_tool\`.

### Acceptance criteria
- [ ] New category added to the taxonomy set
- [ ] \`did_not_use_tool\` uses it
- [ ] README failure-category table updated
- [ ] Unit test asserts the category on failure' \
'["good first issue","enhancement"]'

create_issue \
"Support async agent callables in PythonAdapter" \
'\`PythonAdapter\` (\`invarium/adapters/python.py\`) only supports synchronous callables. Many agents expose an async \`run\`/\`__call__\`.

### Task
Detect coroutine functions / awaitables and run them to completion (e.g. via \`asyncio.run\` / an event loop) so async agents work without a wrapper.

### Acceptance criteria
- [ ] Sync callables keep working unchanged
- [ ] \`async def\` agents are supported
- [ ] Unit tests cover both sync and async paths
- [ ] Documented in the adapters section / ADAPTER_GUIDE.md' \
'["help wanted","enhancement"]'

create_issue \
"Add Ruff linting (config + CI check)" \
'The project has no linter configured. Ruff is fast and a good default.

### Task
- Add Ruff config (in \`pyproject.toml\` under \`[tool.ruff]\` or a \`ruff.toml\`).
- Add a \`ruff\` extra or dev dependency.
- Add a lint job/step to \`.github/workflows/tests.yml\` (or a new \`lint.yml\`) running \`ruff check .\`.

### Acceptance criteria
- [ ] \`ruff check .\` passes on the current codebase (fix or configure rules as needed)
- [ ] CI runs the lint check on push and PR
- [ ] CONTRIBUTING.md mentions running the linter' \
'["good first issue"]'

create_issue \
"Add mypy type checking in CI" \
'The codebase uses type hints but they are not verified. Adding mypy catches type regressions.

### Task
- Add a mypy configuration (start lenient, then tighten).
- Add a dev dependency and a CI step running \`mypy invarium\`.

### Acceptance criteria
- [ ] mypy runs clean on \`invarium/\` (with a documented baseline config)
- [ ] CI runs mypy on push and PR
- [ ] CONTRIBUTING.md notes how to run it' \
'["help wanted"]'

create_issue \
"Add a pre-commit configuration" \
'A \`.pre-commit-config.yaml\` lets contributors catch formatting/lint issues before committing.

### Task
Add \`.pre-commit-config.yaml\` with sensible hooks (e.g. trailing-whitespace, end-of-file-fixer, and Ruff if/when added), and document \`pre-commit install\` in CONTRIBUTING.md.

### Acceptance criteria
- [ ] \`pre-commit run --all-files\` passes
- [ ] Setup documented in CONTRIBUTING.md' \
'["good first issue"]'

create_issue \
"Add runnable examples for the CrewAI and OpenAI Agents adapters" \
'\`examples/\` only contains a plain-Python booking agent. Users on CrewAI and the OpenAI Agents SDK have no copy-pasteable starting point.

### Task
- Add \`examples/crewai_agent.py\` + a test using \`CrewAIAdapter\`.
- Add \`examples/openai_agents_agent.py\` + a test using \`OpenAIAgentsAdapter\`.
- Keep each runnable with the matching extra (\`invarium[crewai]\` / \`invarium[openai]\`).

Follow the pattern in \`examples/booking_agent.py\` and \`examples/test_fake_booking_agent.py\`.

### Acceptance criteria
- [ ] Both examples run with their extra installed
- [ ] Tests use \`pytest.importorskip\` so they skip when the SDK is absent' \
'["good first issue","documentation"]'

create_issue \
"Add Dependabot for GitHub Actions updates" \
'There is no \`.github/dependabot.yml\`, so the GitHub Actions used in workflows wont get automatic update PRs.

### Task
Add \`.github/dependabot.yml\` with a weekly \`github-actions\` update schedule (and optionally \`pip\`).

### Acceptance criteria
- [ ] Dependabot config validates
- [ ] Opens update PRs for outdated actions' \
'["good first issue"]'

echo "Done."
