# LangGraph booking-regression demo

A 30-second, **reproducible** example of the kind of bug Invarium exists to catch:
an agent that **claims success without doing the work**, and a model swap that
silently breaks tool usage while the reply still *looks* perfect.

The agent is deterministic (no LLM / API key), so it behaves identically in CI and
on any machine. The message shapes match what a real LangGraph ReAct agent emits.

## The two versions

| Mode | Behavior |
|---|---|
| `DEMO_REGRESSED` unset (v1, "good") | `search_restaurants` → `book_table` → "Booked! Confirmation BC-2-TONIGHT." |
| `DEMO_REGRESSED=1` (v2, "regressed") | `search_restaurants` → "Booked! Confirmed." — **skips `book_table`** |

v2 simulates a common real-world regression: you upgrade the model, the replies get
*more* fluent, and the agent quietly stops calling a required tool while still telling
the user the action succeeded.

## Run it

From the repo root:

```bash
# 1. Bless the healthy agent as the known-good baseline (passes 5/5)
invarium bless framework_examples/langgraph_booking_regression

# 2. Ship the regression and watch Invarium catch it
DEMO_REGRESSED=1 invarium test framework_examples/langgraph_booking_regression
```

## What you'll see

```
[REGRESSION] test_booking_agent
  Success      100.0% -> 0.0%
  Tool drop    book_table 100.0% -> 0.0%
  Failure cats missing_required_tool:5, wrong_tool_order:5, unsupported_success_claim:5
  - Agent claimed success in final output without evidence from book_table. (5/5 runs)
```

An exact-string test on the final answer passes both versions. An LLM-as-judge on the
text scores the regressed reply *higher* (it's more confident). Invarium fails it,
because it asserts on what the agent **did**, not what it **said**.
