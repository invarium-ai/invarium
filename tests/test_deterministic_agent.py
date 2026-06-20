from __future__ import annotations

from invarium import AgentResult, ToolCall, agent_test, expect


@agent_test(runs=3)
def test_deterministic_agent():
    result = AgentResult(
        input="Research market trends",
        final_output="Completed research with cited sources.",
        tool_calls=[
            ToolCall(name="search_tool", args={"query": "market trends"}),
            ToolCall(name="citation_formatter", args={"count": 3}),
        ],
        steps=2,
    )
    expect(result).used_tool("search_tool")
    expect(result).used_tools_in_order(["search_tool", "citation_formatter"])
    expect(result).steps_less_than(5)
    expect(result).finished_successfully()
    return result
