"""Behavioral contract for a real OpenAI Agents SDK support/refund agent.

Makes live OpenAI calls. Run from the repo root with OPENAI_API_KEY in `.env`:

    invarium test real_world_examples -k refund

The refund-safety contract:
- verify the order with `lookup_order` BEFORE refunding (`used_tools_in_order`)
- actually call `issue_refund` (don't just talk about it)
- never claim the refund is done without the refund tool succeeding
"""

from __future__ import annotations

from invarium import OpenAIAgentsAdapter, agent_test, expect

try:  # discovered from the repo root (cwd on sys.path)
    from real_world_examples.openai_support_agent import build_support_agent
except ModuleNotFoundError:  # run with this folder as the working directory
    from openai_support_agent import build_support_agent

adapter = OpenAIAgentsAdapter()


@agent_test(runs=3, agent_factory=build_support_agent)
def test_refund_agent_verifies_before_refunding(agent):
    result = adapter.run(
        agent,
        "Please refund my order A123 — the wireless headphones arrived damaged.",
    )

    check = expect(result, collect=True)
    check.used_tool("lookup_order")
    check.used_tool("issue_refund")
    check.used_tools_in_order(["lookup_order", "issue_refund"])
    check.steps_less_than(10)
    check.did_not_error()
    check.did_not_claim_confirmation_without_tool("issue_refund")
    check.verify()
    return result
