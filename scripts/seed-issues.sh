#!/usr/bin/env bash
#
# Seed good-first-issues / help-wanted issues for invarium-ai/invarium.
#
# Usage:
#   GH_TOKEN=ghp_yourtoken bash scripts/seed-issues.sh
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
"Add a latency_less_than(ms) assertion" \
'\`AgentResult\` already carries a \`latency\` field (\`invarium/result.py\`) and the failure taxonomy already defines a \`latency_exceeded\` category (\`invarium/assertions.py\`), but there is no assertion that uses them.

### Task
Add an \`Expectation.latency_less_than(limit_ms: float)\` method in \`invarium/assertions.py\` that:
- passes when \`result.latency\` is not None and \`< limit_ms\`
- fails with category \`latency_exceeded\` otherwise (including when latency is None — message should make that clear)

### Acceptance criteria
- [ ] Method follows the existing \`_check(...)\` pattern
- [ ] Add it to the assertions list in \`README.md\`
- [ ] Add a unit test under \`tests/\`

Good place to learn the assertion pattern: look at \`steps_less_than\` for a near-identical shape.' \
'["good first issue","enhancement"]'

create_issue \
"Add a cost_less_than(amount) assertion" \
'\`AgentResult\` carries a \`cost\` field and the taxonomy defines a \`cost_exceeded\` category, but no assertion uses them.

### Task
Add \`Expectation.cost_less_than(limit: float)\` in \`invarium/assertions.py\`:
- passes when \`result.cost\` is not None and \`< limit\`
- fails with category \`cost_exceeded\` otherwise

### Acceptance criteria
- [ ] Mirror the structure of \`steps_less_than\` / the proposed \`latency_less_than\`
- [ ] Document it in \`README.md\`
- [ ] Add a unit test under \`tests/\`' \
'["good first issue","enhancement"]'

create_issue \
"Document the tool_called_with_args assertion in the README" \
'The \`tool_called_with_args(tool_name, expected_args)\` assertion exists in \`invarium/assertions.py\` but is missing from the assertions list in \`README.md\`.

### Task
- [ ] Add it to the "Assertions" code block in \`README.md\`
- [ ] Add a short example showing a subset-match against tool args
- [ ] Add it to the failure-category table (maps to \`wrong_tool_args\`)

No code changes required — documentation only. Great first PR.' \
'["good first issue","documentation"]'

create_issue \
"Support regex flags in final_output_matches_pattern" \
'\`final_output_matches_pattern(pattern)\` in \`invarium/assertions.py\` calls \`re.search(pattern, ...)\` with no way to pass flags (e.g. case-insensitive matching).

### Task
Add an optional \`flags: int = 0\` parameter:
\`\`\`python
def final_output_matches_pattern(self, pattern: str, flags: int = 0) -> "Expectation":
    matched = bool(re.search(pattern, self.result.final_output, flags))
\`\`\`

### Acceptance criteria
- [ ] Backwards compatible (default \`flags=0\`)
- [ ] Unit test covering \`re.IGNORECASE\`
- [ ] Note the new parameter in \`README.md\`' \
'["good first issue","enhancement"]'

create_issue \
"Add a runnable example for the LangGraph adapter" \
'The \`examples/\` folder only has a booking-agent example for the plain Python adapter. New users adopting LangGraph have no copy-pasteable starting point.

### Task
- [ ] Add \`examples/langgraph_agent.py\` with a minimal LangGraph \`StateGraph\` agent
- [ ] Add a behavioral test using \`LangGraphAdapter\` (\`invarium/adapters/langgraph.py\`)
- [ ] Keep it runnable with \`pip install "invarium[langgraph]"\`

See \`examples/booking_agent.py\` and \`examples/test_fake_booking_agent.py\` for the existing pattern.' \
'["good first issue","documentation"]'

create_issue \
"New adapter: smolagents" \
'We support OpenAI Agents, LangGraph, CrewAI, plain Python, and HTTP. A common request is Hugging Face **smolagents**.

### Task
Implement \`SmolagentsAdapter\` that normalizes a smolagents run into our \`AgentResult\` / \`ToolCall\` model.

### Pointers
- Adapter base + contract: \`invarium/adapters/base.py\`
- Skeleton to copy: \`invarium/adapters/template.py\`
- Reference implementation: \`invarium/adapters/crewai.py\`
- Wire it up in \`invarium/adapters/__init__.py\` and add an optional extra in \`pyproject.toml\`

### Acceptance criteria
- [ ] Maps tool calls, steps, final output, and errors
- [ ] Unit test with a fake/mocked smolagents object
- [ ] README adapter table updated' \
'["help wanted","enhancement"]'

create_issue \
"New adapter: AutoGen" \
'Add an adapter for Microsoft **AutoGen** agents/teams.

### Task
Implement \`AutoGenAdapter\` mapping an AutoGen run into \`AgentResult\` / \`ToolCall\`.

### Pointers
- \`invarium/adapters/base.py\` (contract), \`invarium/adapters/template.py\` (skeleton)
- Existing example to follow: \`invarium/adapters/openai_agents.py\`
- Register in \`invarium/adapters/__init__.py\`; add a \`[autogen]\` extra in \`pyproject.toml\`

### Acceptance criteria
- [ ] Tool calls + steps + final output normalized
- [ ] Unit test with a mocked AutoGen result
- [ ] README adapter table updated' \
'["help wanted","enhancement"]'

create_issue \
"New adapter: Pydantic AI" \
'Add an adapter for **Pydantic AI** agents.

### Task
Implement \`PydanticAIAdapter\` that converts a Pydantic AI run result into \`AgentResult\` / \`ToolCall\`.

### Pointers
- Contract: \`invarium/adapters/base.py\`; skeleton: \`invarium/adapters/template.py\`
- Register in \`invarium/adapters/__init__.py\`; add a \`[pydantic-ai]\` extra in \`pyproject.toml\`

### Acceptance criteria
- [ ] Normalizes tool calls, steps, final output, errors
- [ ] Unit test with a mocked run
- [ ] README adapter table updated' \
'["help wanted","enhancement"]'

echo "Done."
