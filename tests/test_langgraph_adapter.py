from __future__ import annotations

from typing import Annotated, TypedDict

import pytest

pytest.importorskip("langchain_core.messages")
pytest.importorskip("langgraph.graph")

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, add_messages

from invarium import LangGraphAdapter


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]


def test_langgraph_adapter_normalizes_message_state_with_tool_calls():
    adapter = LangGraphAdapter()
    raw_result = {
        "messages": [
            HumanMessage(content="What is Invarium?"),
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
                content="Invarium is a behavioral testing library.",
                tool_call_id="call_1",
                name="search_docs",
            ),
            AIMessage(content="Invarium tests agent behavior."),
        ],
        "errors": [],
    }

    result = adapter.normalize("What is Invarium?", raw_result)

    assert result.final_output == "Invarium tests agent behavior."
    assert result.steps == 3
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search_docs"
    assert result.tool_calls[0].args == {"query": "Invarium"}
    assert result.tool_calls[0].output == "Invarium is a behavioral testing library."
    assert result.messages[0]["role"] == "user"
    assert result.messages[-1]["role"] == "assistant"
    assert result.metadata["adapter"] == "langgraph"


def test_langgraph_adapter_runs_real_compiled_graph():
    adapter = LangGraphAdapter()

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
                    content="Invarium is a behavioral testing library.",
                    tool_call_id="call_1",
                    name="search_docs",
                ),
                AIMessage(content="Invarium tests agent behavior."),
            ]
        }

    builder = StateGraph(GraphState)
    builder.add_node("respond", respond)
    builder.set_entry_point("respond")
    builder.set_finish_point("respond")
    graph = builder.compile()

    result = adapter.run(graph, "What is Invarium?")

    assert result.final_output == "Invarium tests agent behavior."
    assert [tool.name for tool in result.tool_calls] == ["search_docs"]
    assert result.steps == 3
