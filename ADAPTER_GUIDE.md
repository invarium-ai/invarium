# Invarium Adapter Guide

This guide explains how adapters should be structured in Invarium.

## Why Adapters Exist

Every agent framework exposes execution state differently.

Some give you:

- messages
- tool calls
- outputs
- errors
- intermediate events

Others only give you:

- a final response
- maybe a tool trace

Invarium uses adapters to normalize those differences into one shared model:

- `AgentResult`
- `ToolCall`

That is what allows the same assertions to work across different frameworks.

## Current Adapter Location

All adapters should live in:

```text
invarium/adapters/
```

Current files:

- `base.py`
- `langgraph.py`
- `python.py`
- `openai_agents.py`
- `template.py`

## Minimal Contract

Each adapter should follow this pattern:

1. `run(agent, prompt)` executes the framework-specific agent call
2. `normalize(prompt, raw_result)` converts the raw framework output into `AgentResult`

This is the intended contract exposed by `BaseAdapter`.

## Normalization Target

Every adapter should normalize into:

```python
AgentResult(
    input=...,
    final_output=...,
    messages=[...],
    tool_calls=[...],
    steps=...,
    errors=[...],
    metadata={...},
)
```

Tool usage should be represented with:

```python
ToolCall(
    name=...,
    args=...,
    output=...,
    success=...,
    timestamp=...,
)
```

## What to Normalize

### Required

- final output
- tool calls
- step count
- errors

### Strongly Recommended

- message-like events
- framework metadata useful for debugging

### Optional

- latency
- cost

If a framework does not expose some fields, leave them empty or `None`.

## Step Counting Guidance

Steps should represent logical agent actions, not necessarily raw event count.

Good examples:

- one model reasoning turn
- one tool invocation
- one assistant output step

Avoid inflating steps with bookkeeping-only events.

The goal is for step-based assertions to feel meaningful to developers.

## Metadata Guidance

Use `result.metadata` for framework-specific extras that are useful but should
not leak into generic assertions.

Good examples:

- framework name
- usage or token metadata
- raw item count
- trace IDs

Do not rely on metadata for core assertion behavior unless absolutely necessary.

## Error Handling Guidance

Adapters should surface:

- run-level exceptions
- framework-reported errors
- tool-level errors when observable

Normalize them into `result.errors` as human-readable strings where possible.

## Recommended Adapter Shape

Start from:

- [invarium/adapters/template.py](invarium/adapters/template.py)

Basic pattern:

```python
class MyFrameworkAdapter(BaseAdapter):
    def run(self, agent, prompt):
        raw_result = ...
        return self.normalize(prompt, raw_result)

    def normalize(self, prompt, raw_result):
        ...
        return AgentResult(...)
```

## How to Build a New Adapter

### Step 1. Understand the framework output

Figure out how the framework exposes:

- tool calls
- final output
- messages or intermediate items
- errors
- step-like units

### Step 2. Map tool calls

Identify:

- tool name
- arguments
- output
- success state
- timestamps if available

### Step 3. Map the final output

Extract the final user-visible answer as a string.

### Step 4. Count logical steps

Avoid counting internal framework noise if it does not represent a real behavior step.

### Step 5. Preserve useful extras in metadata

Keep the normalized result small, but include debugging context in metadata.

### Step 6. Add tests

Every adapter should have at least:

- one normalization test using realistic sample data
- one real integration example if feasible

## Good Adapter Design Principles

- keep framework-specific logic inside the adapter
- keep normalized outputs simple
- avoid exposing raw framework objects to assertions
- prefer stable fields over clever framework-specific shortcuts
- optimize for maintainability, not maximum abstraction

## What Not to Do

- do not design one giant generic adapter engine
- do not leak framework-specific event types into assertions
- do not over-model every possible raw event unless users need it
- do not optimize for every framework before demand exists

## Recommended Next Adapters

Likely high-value next targets:

- CrewAI
- another framework only if users ask for it

### Async Python Agents

`PythonAdapter` supports both synchronous and asynchronous agent callables.

```python
from invarium.adapters.python import PythonAdapter

class AsyncAgent:
    async def run(self, prompt):
        return {
            "input": prompt,
            "final_output": "done",
        }

adapter = PythonAdapter()
result = adapter.run(AsyncAgent(), "hello")
```

Async results are automatically awaited before being normalized into an `AgentResult`.

## Summary

The adapter layer should stay small and boring.

That is a good thing.

Its job is simply:

- run the framework-specific agent
- normalize the output into `AgentResult`
- get out of the way
