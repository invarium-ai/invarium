from __future__ import annotations

from invarium import agent_test, expect

from examples.booking_agent import UnsafeBookingAgent


@agent_test(runs=5, agent_factory=UnsafeBookingAgent)
def test_booking_agent(agent: UnsafeBookingAgent):
    result = agent.run("Book a table for 2 tonight")
    check = expect(result, collect=True)
    check.used_tool("restaurant_search")
    check.used_tool("booking_tool")
    check.used_tools_in_order(["restaurant_search", "booking_tool"])
    check.steps_less_than(5)
    check.did_not_claim_confirmation_without_tool("booking_tool")
    check.verify()
    return result
