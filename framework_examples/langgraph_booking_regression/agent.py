"""A small but realistic LangGraph booking agent with a regression baked in.

Two behaviors live behind one env flag so we can demonstrate a *behavioral
regression* that exact-text tests miss entirely:

- ``DEMO_REGRESSED`` unset -> v1 "good" agent:
  ``search_restaurants`` -> ``book_table`` -> "Booked! Confirmation BC-2-TONIGHT."
- ``DEMO_REGRESSED=1`` -> v2 "regressed" agent (e.g. after a model/prompt swap):
  it SKIPS ``book_table`` but still tells the user "Booked! Confirmed."

The node is deterministic (no LLM / API key), so the demo reproduces identically
in CI or on anyone's laptop. The message shapes are exactly what a real LangGraph
ReAct agent emits, so Invarium's ``LangGraphAdapter`` reads it the same way.
"""

from __future__ import annotations

import os
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, add_messages


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]


def _regressed() -> bool:
    return os.environ.get("DEMO_REGRESSED", "") not in ("", "0", "false", "False")


def build_graph():
    def agent_node(state: GraphState):
        # Step 1: check availability (both versions do this correctly).
        search_call = {
            "name": "search_restaurants",
            "args": {"party_size": 2, "when": "tonight"},
            "id": "call_search_1",
            "type": "tool_call",
        }
        search_result = ToolMessage(
            content='{"restaurant": "Bombay Canteen", "available": true}',
            tool_call_id="call_search_1",
            name="search_restaurants",
        )

        if _regressed():
            # v2: the "upgraded" model gets chatty and confident, skips the
            # booking tool entirely, but still claims the table is booked.
            return {
                "messages": [
                    AIMessage(content="Let me check availability.", tool_calls=[search_call]),
                    search_result,
                    AIMessage(
                        content=(
                            "Booked your table at Bombay Canteen for 2 tonight. "
                            "Your reservation is confirmed!"
                        )
                    ),
                ]
            }

        # v1: actually calls book_table before confirming.
        book_call = {
            "name": "book_table",
            "args": {"restaurant": "Bombay Canteen", "party_size": 2, "when": "tonight"},
            "id": "call_book_1",
            "type": "tool_call",
        }
        book_result = ToolMessage(
            content='{"confirmation_id": "BC-2-TONIGHT", "status": "confirmed"}',
            tool_call_id="call_book_1",
            name="book_table",
        )
        return {
            "messages": [
                AIMessage(content="Let me check availability.", tool_calls=[search_call]),
                search_result,
                AIMessage(content="Found a table. Booking it now.", tool_calls=[book_call]),
                book_result,
                AIMessage(
                    content=(
                        "Booked your table at Bombay Canteen for 2 tonight. "
                        "Confirmation: BC-2-TONIGHT."
                    )
                ),
            ]
        }

    builder = StateGraph(GraphState)
    builder.add_node("agent", agent_node)
    builder.set_entry_point("agent")
    builder.set_finish_point("agent")
    return builder.compile()
