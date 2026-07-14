# Testing Perseus agents with Invarium

A 30-second, **reproducible** example of *context-regression testing*: proving that
when an agent's pre-loaded context changes, its behavior changes predictably — and
when the context shouldn't change, the behavior doesn't drift.

[Perseus](https://perseus.observer) is a context engine for AI agents. Before a
session starts, Perseus pre-loads context — files, memory, and services — and
injects a stable **`context_hash`** into the session metadata. That hash is the
fingerprint of *exactly what the agent was given to reason over*. Invarium is a
natural fit: Perseus's "pre-load context → agent runs → assert on tool calls and
order" flow maps directly onto `used_tools_in_order([...])`, step budgets, and the
"didn't-claim-success-without-the-tool" check, and the `bless`/`compare` baseline
flow is built for catching *behavioral* regressions across those context changes.

The agent here is deterministic (no LLM / API key, standard library only), so it
behaves identically in CI and on any machine. The metadata shape matches what a
real Perseus adapter surfaces, so Invarium's `PythonAdapter` reads it the same way.

## The pattern

1. **Perseus pre-loads context** and injects a `context_hash` into session metadata.
2. **The agent runs** with that context. Its result carries the hash in
   [`AgentResult.metadata`](../../invarium/result.py) — the free-form channel
   Invarium preserves end to end (adapter → normalization → JSON traces).
3. **Invarium asserts on both** the context the agent ran against *and* the behavior
   it produced:
   - **context** — `assert result.metadata["context_hash"] == EXPECTED` (works today)
   - **behavior** — `used_tools_in_order([...])`, `did_not_claim_confirmation_without_tool(...)`

Together those prove the regression story: *when `context_hash` changes, the tool
path changes predictably; when it shouldn't change, it doesn't.*

## The two versions

| Mode | Behavior |
|---|---|
| `PERSEUS_CONTEXT_DRIFT` unset (v1, "good") | Perseus loads the Q3 doc → agent calls `retrieve` → `answer`, grounded in `reports/q3.md` |
| `PERSEUS_CONTEXT_DRIFT=1` (v2, "regressed") | The Q3 doc falls out of the loaded context → agent **skips `retrieve`** and answers from its prior, still claiming the summary "completed successfully" |

v2 simulates a common real-world context regression: a broken include, a stale
memory store, or an expired service token silently drops a document from the
bundle. The reply still *looks* complete — an exact-string test passes and an
LLM-as-judge may even score the ungrounded answer higher because it reads more
confidently. Invarium fails it, because the `context_hash` changed **and** the
agent stopped grounding its answer.

## The full flow

The example is wired for the same "bless a known-good baseline, then catch
regressions" loop as the rest of Invarium.

```python
# framework_examples/perseus_context_regression/test_perseus_agent.py
from invarium import PythonAdapter, agent_test, expect
from agent import EXPECTED_CONTEXT_HASH, build_agent

adapter = PythonAdapter()


@agent_test(runs=5, agent_factory=build_agent)
def test_perseus_grounded_answer(agent):
    result = adapter.run(agent, "Summarize the Q3 revenue doc")

    # (1) Context assertion — works today via AgentResult.metadata.
    # Perseus injects `context_hash`; the adapter surfaces it unchanged.
    assert result.metadata["context_hash"] == EXPECTED_CONTEXT_HASH

    # (2) Behavioral assertions on top.
    check = expect(result, collect=True)
    check.used_tool("retrieve")
    check.used_tools_in_order(["retrieve", "answer"])
    check.did_not_claim_confirmation_without_tool("retrieve")
    check.steps_less_than(6)
    check.did_not_error()
    check.verify()
    return result
```

On the Perseus side, the adapter's only job is to put the injected hash on the
result — Invarium carries it the rest of the way:

```python
# framework_examples/perseus_context_regression/agent.py (abridged)
bundle, context_hash = perseus_preload()        # Perseus pre-loads + fingerprints
return AgentResult(
    input=prompt,
    final_output=summary,
    tool_calls=[ToolCall("retrieve", ...), ToolCall("answer", ...)],
    steps=2,
    metadata={"context_hash": context_hash, "loaded_files": sorted(bundle)},
)
```

## Run it

From the repo root:

```bash
# 1. Bless the healthy agent against the known-good context (passes 5/5)
invarium bless framework_examples/perseus_context_regression

# 2. Drift the context and watch Invarium catch it
PERSEUS_CONTEXT_DRIFT=1 invarium test framework_examples/perseus_context_regression
```

## What you'll see

Blessing the good version records the grounded tool path as the baseline:

```
[PASS] test_perseus_grounded_answer
  Runs         5
  Passed       5
  Success      100.0%
  Tools        answer 100.0%, retrieve 100.0%
  Path         retrieve -> answer (100.0%)
```

Drift the context and the same test fails on the `context_hash` mismatch, and the
baseline comparison flags the behavioral regression:

```
[FAIL] test_perseus_grounded_answer
  Runs         5
  Passed       0
  Failed       5
  Failures
    - context drifted: agent ran against 318a28cc... (loaded ['memory/company_facts.md']),
      expected 8e77a37e... (5/5 runs)

[REGRESSION] test_perseus_grounded_answer
  Success      100.0% -> 0.0%
  Path         retrieve -> answer (100.0%) -> (no tools) (0.0%)
  Tool drop    retrieve 100.0% -> 0.0%
```

## Coming soon: first-class context assertions (#26)

Today the context check is a plain `assert` on `result.metadata["context_hash"]`.
It works, but because a raised assertion aborts the run, a context mismatch lands
under the generic `runtime_error` category. [Issue #26](https://github.com/invarium-ai/invarium/issues/26)
tracks promoting this to first-class assertions that *collect* alongside the
behavioral findings and participate in the report and `compare`:

```python
expect(result).metadata_equals("context_hash", expected)
expect(result).metadata_contains("loaded_files")
# stretch: expect(result).context_changed(baseline)  # ties into bless/compare
```

with a dedicated **`context_mismatch`** failure category — so a single report shows
both *that the context changed* and *how the behavior drifted* in one place.

---

*Contributed by [Perseus Computing LLC](https://perseus.observer) — see
[issue #20](https://github.com/invarium-ai/invarium/issues/20).*
