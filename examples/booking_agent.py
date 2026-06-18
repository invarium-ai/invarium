from __future__ import annotations

from dataclasses import dataclass

from invarium import AgentResult, ToolCall


@dataclass(slots=True)
class SearchResult:
    restaurant_name: str
    available: bool


@dataclass(slots=True)
class BookingReceipt:
    confirmation_id: str
    restaurant_name: str


class RestaurantSearchTool:
    def run(self, *, party_size: int, time_hint: str) -> SearchResult:
        return SearchResult(
            restaurant_name="Bombay Canteen",
            available=party_size <= 4 and "tonight" in time_hint.lower(),
        )


class BookingTool:
    def run(self, *, restaurant_name: str, party_size: int) -> BookingReceipt:
        confirmation_id = f"{restaurant_name.lower().replace(' ', '-')}-{party_size}"
        return BookingReceipt(
            confirmation_id=confirmation_id,
            restaurant_name=restaurant_name,
        )


class SimpleBookingAgent:
    def __init__(
        self,
        *,
        search_tool: RestaurantSearchTool | None = None,
        booking_tool: BookingTool | None = None,
        unsafe_confirm_without_booking: bool = False,
    ) -> None:
        self.search_tool = search_tool or RestaurantSearchTool()
        self.booking_tool = booking_tool or BookingTool()
        self.unsafe_confirm_without_booking = unsafe_confirm_without_booking

    def run(self, prompt: str) -> AgentResult:
        tool_calls: list[ToolCall] = []
        steps = 0

        search = self.search_tool.run(party_size=2, time_hint=prompt)
        tool_calls.append(
            ToolCall(
                name="restaurant_search",
                args={"party_size": 2, "time_hint": prompt},
                output={
                    "restaurant_name": search.restaurant_name,
                    "available": search.available,
                },
            )
        )
        steps += 1

        if not search.available:
            return AgentResult(
                input=prompt,
                final_output="I could not find availability tonight.",
                tool_calls=tool_calls,
                steps=steps,
                metadata={"agent": "simple-booking-agent"},
            )

        if self.unsafe_confirm_without_booking:
            return AgentResult(
                input=prompt,
                final_output=f"Booked a table at {search.restaurant_name} for 2 tonight.",
                tool_calls=tool_calls,
                steps=steps + 1,
                metadata={"agent": "simple-booking-agent", "mode": "unsafe"},
            )

        receipt = self.booking_tool.run(
            restaurant_name=search.restaurant_name,
            party_size=2,
        )
        tool_calls.append(
            ToolCall(
                name="booking_tool",
                args={"restaurant_name": search.restaurant_name, "party_size": 2},
                output={
                    "confirmation_id": receipt.confirmation_id,
                    "restaurant_name": receipt.restaurant_name,
                },
            )
        )
        steps += 1

        return AgentResult(
            input=prompt,
            final_output=(
                f"Booked a table at {receipt.restaurant_name} for 2 tonight. "
                f"Confirmation: {receipt.confirmation_id}."
            ),
            tool_calls=tool_calls,
            steps=steps,
            metadata={"agent": "simple-booking-agent", "mode": "safe"},
        )


class UnsafeBookingAgent(SimpleBookingAgent):
    def __init__(self) -> None:
        super().__init__(unsafe_confirm_without_booking=True)
