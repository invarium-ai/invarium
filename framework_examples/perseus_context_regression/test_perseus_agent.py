"""Invarium behavioral contract for a Perseus-powered context-aware agent.

Two things are asserted together, and that pairing is the whole point:

1. **Context** — the agent ran against the ``context_hash`` we blessed. This uses
   ``AgentResult.metadata``, the free-form channel Invarium preserves end to end,
   and works today with a plain ``assert``.
2. **Behavior** — given that context, the agent grounded its answer by calling
   ``retrieve`` before ``answer``, and never claimed success without the tool.

When Perseus's pre-loaded context drifts, (1) catches *that the inputs changed* and
(2) catches *that the behavior degraded*. Together they prove the context-regression
story: when ``context_hash`` changes, the tool path changes predictably; when it
shouldn't change, it doesn't.

Run it from the repo root:

    invarium bless framework_examples/perseus_context_regression
    PERSEUS_CONTEXT_DRIFT=1 invarium test framework_examples/perseus_context_regression
"""

from __future__ import annotations

from invarium import PythonAdapter, agent_test, expect

try:  # discovered from the repo root (cwd on sys.path)
    from framework_examples.perseus_context_regression.agent import (
        EXPECTED_CONTEXT_HASH,
        build_agent,
    )
except ModuleNotFoundError:  # run with this folder as the working directory
    from agent import EXPECTED_CONTEXT_HASH, build_agent

adapter = PythonAdapter()


@agent_test(runs=5, agent_factory=build_agent)
def test_perseus_grounded_answer(agent):
    result = adapter.run(agent, "Summarize the Q3 revenue doc")

    # (1) Context assertion — works today via AgentResult.metadata.
    # Perseus injects `context_hash`; the PythonAdapter surfaces it unchanged.
    assert result.metadata["context_hash"] == EXPECTED_CONTEXT_HASH, (
        "context drifted: agent ran against "
        f"{result.metadata['context_hash']} (loaded {result.metadata['loaded_files']}), "
        f"expected {EXPECTED_CONTEXT_HASH}"
    )

    # (2) Behavioral assertions on top — collected so the report shows every failure.
    check = expect(result, collect=True)
    check.used_tool("retrieve")
    check.used_tools_in_order(["retrieve", "answer"])
    check.did_not_claim_confirmation_without_tool("retrieve")
    check.steps_less_than(6)
    check.did_not_error()
    check.verify()
    return result
