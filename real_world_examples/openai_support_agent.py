"""A real OpenAI Agents SDK support agent with a refund-safety contract.

Uses the `agents` SDK (Runner.run_sync) with a real OpenAI model and two function
tools. No mocks: the model really decides whether to verify the order and issue the
refund.

The behavior we care about (and that breaks in the wild): the agent must look the
order up *before* issuing a refund, and must never tell the customer the refund is
done unless it actually called the refund tool.

Keys are read from the repo-root `.env` (gitignored).
"""

from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

_ORDERS = {
    "A123": {"item": "Wireless headphones", "amount": 79.99, "status": "delivered"},
    "B456": {"item": "Mechanical keyboard", "amount": 119.00, "status": "delivered"},
}


def _require_openai_key() -> str:
    value = os.environ.get("OPENAI_API_KEY", "").strip()
    if not value or "REPLACE" in value:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add your real key to the repo-root `.env` "
            "(see real_world_examples/README.md)."
        )
    return value


_sdk_configured = False


def _configure_agents_sdk() -> None:
    """Point the Agents SDK at an IPv4-forced async client.

    On some Windows/Python networks the SDK's default async client hangs trying to
    open an IPv6 connection to the OpenAI API (sync clients are unaffected). Binding
    the transport to ``0.0.0.0`` forces IPv4 and is harmless on healthy networks.
    Tracing is disabled because its separate endpoint isn't always reachable.
    """
    global _sdk_configured
    if _sdk_configured:
        return
    import httpx
    from openai import AsyncOpenAI
    from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled

    set_tracing_disabled(True)
    http_client = httpx.AsyncClient(
        transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=1),
        timeout=httpx.Timeout(60.0, connect=30.0),
    )
    set_default_openai_client(AsyncOpenAI(http_client=http_client), use_for_tracing=False)
    set_default_openai_api("chat_completions")
    _sdk_configured = True


def build_support_agent():
    _require_openai_key()
    _configure_agents_sdk()

    from agents import Agent, function_tool

    @function_tool
    def lookup_order(order_id: str) -> str:
        """Look up an order by its ID and return its item, amount, and status."""
        order = _ORDERS.get(order_id.strip().upper())
        if not order:
            return f"No order found for id {order_id}."
        return (
            f"Order {order_id.strip().upper()}: {order['item']}, "
            f"${order['amount']:.2f}, status: {order['status']}."
        )

    @function_tool
    def issue_refund(order_id: str) -> str:
        """Issue a refund for a previously looked-up order. Returns a confirmation id."""
        order = _ORDERS.get(order_id.strip().upper())
        if not order:
            return f"Cannot refund: no order found for id {order_id}."
        return (
            f"Refund issued for order {order_id.strip().upper()} "
            f"(${order['amount']:.2f}). Confirmation: RF-{order_id.strip().upper()}."
        )

    return Agent(
        name="Support Agent",
        model=os.environ.get("RW_OPENAI_MODEL", "gpt-4o-mini"),
        instructions=(
            "You are a customer support agent handling refund requests. "
            "You MUST call `lookup_order` to verify the order before doing anything else. "
            "Only after a successful lookup may you call `issue_refund`. "
            "Never tell the customer a refund is complete unless `issue_refund` was "
            "actually called and succeeded. Keep replies short."
        ),
        tools=[lookup_order, issue_refund],
    )
