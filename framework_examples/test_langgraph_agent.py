from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, add_messages

from invarium import LangGraphAdapter, agent_test, expect


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]


def build_graph():
    def respond(state: GraphState):
        return {
            "messages": [
                AIMessage(
                    content="Let me search.",
                    tool_calls=[
                        {
                            "name": "search_docs",
                            "args": {"query": "Invarium"},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                ),
                ToolMessage(
                    content=(
                        "Invarium is a behavioral testing library for repeated runs, "
                        "tool usage assertions, and regression detection."
                    ),
                    tool_call_id="call_1",
                    name="search_docs",
                ),
                AIMessage(content="Invarium tests agent behavior with assertions and baselines."),
            ]
        }

    builder = StateGraph(GraphState)
    builder.add_node("respond", respond)
    builder.set_entry_point("respond")
    builder.set_finish_point("respond")
    return builder.compile()


adapter = LangGraphAdapter()


@agent_test(runs=3, agent_factory=build_graph)
def test_langgraph_research_agent(graph):
    result = adapter.run(graph, "What does Invarium do?")

    check = expect(result, collect=True)
    check.used_tool("search_docs")
    check.used_tool_times("search_docs", 1)
    check.used_tools_in_order(["search_docs"])
    check.steps_less_than(6)
    check.final_output_contains("Invarium")
    check.did_not_error()
    check.did_not_claim_confirmation_without_tool("search_docs")
    check.verify()
    return result
