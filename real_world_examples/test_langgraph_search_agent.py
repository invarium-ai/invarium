"""Behavioral contract for a real LangGraph ReAct search agent.

This makes live LLM + Tavily calls. Run it from the repo root with keys in `.env`:

    invarium test real_world_examples -k search

We assert on behavior, not wording:
- a factual question must be grounded with a real `tavily_search` call
  (the agent must not answer from memory)
- search must not run away (bounded calls / steps)
- the run must finish without errors and not claim success it can't back up
"""

from __future__ import annotations

from invarium import LangGraphAdapter, agent_test, expect

try:  # discovered from the repo root (cwd on sys.path)
    from real_world_examples.langgraph_search_agent import build_search_agent
except ModuleNotFoundError:  # run with this folder as the working directory
    from langgraph_search_agent import build_search_agent

adapter = LangGraphAdapter()


@agent_test(runs=3, agent_factory=build_search_agent)
def test_search_agent_grounds_with_web_search(graph):
    result = adapter.run(
        graph,
        "Use web search to find who the current CEO of OpenAI is. "
        "Answer in one short sentence.",
    )

    check = expect(result, collect=True)
    check.used_tool("tavily_search")            # must ground the answer in a real search
    check.used_tool_at_most("tavily_search", 3)  # no runaway search loop
    check.steps_less_than(8)
    check.did_not_error()
    check.finished_successfully()
    check.did_not_claim_confirmation_without_tool()
    check.verify()
    return result


@agent_test(runs=2, agent_factory=build_search_agent)
def test_search_agent_uses_calculator_for_math(graph):
    result = adapter.run(
        graph,
        "What is 1234 multiplied by 5678? Use the calculator tool and give just the number.",
    )

    check = expect(result, collect=True)
    check.used_tool("calculator")               # must compute with the tool, not guess
    check.did_not_use_tool("tavily_search")      # arithmetic shouldn't trigger a web search
    check.steps_less_than(8)
    check.did_not_error()
    check.final_output_contains("7006652")       # 1234 * 5678 = 7006652
    check.verify()
    return result
