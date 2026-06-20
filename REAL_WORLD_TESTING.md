# Real-World Testing

Invarium is ready to test real agents, not just the included demo.

## Best First Target

Start with the OpenAI Agents SDK:

- Repo: `openai/openai-agents-python`
- Docs: `https://openai.github.io/openai-agents-python/quickstart/`
- Tools guide: `https://openai.github.io/openai-agents-python/tools/`

Why this is the best first target:

- It is maintained by OpenAI.
- It has a simple Python API.
- Tool use is explicit, which fits Invarium well.
- The public repo includes examples such as `examples/basic`, `examples/tools`, and `examples/research_bot`.

## Install

```bash
python -m pip install openai-agents
```

Set your API key:

```bash
$env:OPENAI_API_KEY="sk-..."
```

Verify it is visible:

```bash
python -c "import os; print(bool(os.environ.get('OPENAI_API_KEY')))"
```

## Starter Pattern

```python
from agents import Agent, function_tool

from invarium import OpenAIAgentsAdapter, agent_test, expect


@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a city."""
    return f"The weather in {city} is sunny."


def build_agent() -> Agent:
    return Agent(
        name="Weather Assistant",
        instructions="Use the weather tool whenever the user asks for weather.",
        tools=[get_weather],
    )


adapter = OpenAIAgentsAdapter()


@agent_test(runs=3, agent_factory=build_agent)
def test_weather_agent(agent: Agent):
    result = adapter.run(agent, "What's the weather in Paris?")

    check = expect(result, collect=True)
    check.used_tool("get_weather")
    check.steps_less_than(6)
    check.did_not_claim_confirmation_without_tool("get_weather")
    check.verify()
    return result
```

Run it with either:

```bash
invarium test .
```

or:

```bash
python -m pytest -q
```

## Included Live Test

This repo now includes a real runnable OpenAI Agents SDK test:

```bash
python -m pytest integration_examples -q
```

or:

```bash
python -m invarium.cli test integration_examples
```

File:

- `integration_examples/test_openai_agents_live.py`

This test:

- creates a real OpenAI agent
- exposes a real function tool called `get_weather`
- prompts the agent with a weather question
- verifies the agent used the tool and answered cleanly

The same file also includes a multi-tool research workflow test:

- `test_openai_research_agent`

That test verifies:

- `search_docs` was used
- `summarize_notes` was used
- tools were used in order
- the run stayed under a step budget

## Recommended Public Examples

Use one of these first:

1. `openai/openai-agents-python/examples/tools`
2. `openai/openai-agents-python/examples/research_bot`
3. `openai/openai-agents-python/examples/basic/hello_world.py` for a smoke test only

## Good First Assertions

- `used_tool(...)`
- `used_tools_in_order([...])`
- `steps_less_than(...)`
- `did_not_claim_confirmation_without_tool(...)`
- `did_not_error()`
