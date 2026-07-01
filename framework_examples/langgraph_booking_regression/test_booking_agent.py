"""Invarium behavioral contract for the LangGraph booking agent.

We don't assert on the exact wording of the reply (it changes between models).
We assert on *behavior*: it must actually call ``book_table``, in order, and must
not claim the table is booked without tool evidence.

Run it from the repo root:

    invarium bless framework_examples/langgraph_booking_regression
    DEMO_REGRESSED=1 invarium test framework_examples/langgraph_booking_regression
"""

from __future__ import annotations

from invarium import LangGraphAdapter, agent_test, expect

try:  # discovered from the repo root (cwd on sys.path)
    from framework_examples.langgraph_booking_regression.agent import build_graph
except ModuleNotFoundError:  # run with this folder as the working directory
    from agent import build_graph

adapter = LangGraphAdapter()


@agent_test(runs=5, agent_factory=build_graph)
def test_booking_agent(graph):
    result = adapter.run(graph, "Book a table for 2 tonight")

    check = expect(result, collect=True)
    check.used_tool("search_restaurants")
    check.used_tool("book_table")
    check.used_tools_in_order(["search_restaurants", "book_table"])
    check.steps_less_than(8)
    check.did_not_error()
    check.did_not_claim_confirmation_without_tool("book_table")
    check.verify()
    return result
