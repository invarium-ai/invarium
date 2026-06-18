from __future__ import annotations

import os

from invarium import OpenAIAgentsAdapter, agent_test, expect


def _require_openai_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. In PowerShell run: "
            "$env:OPENAI_API_KEY='sk-...'"
        )
    return api_key


def build_weather_agent():
    _require_openai_key()

    from agents import Agent, function_tool

    @function_tool
    def get_weather(city: str) -> str:
        """Get the weather for a city."""
        normalized = city.strip().lower()
        forecasts = {
            "paris": "Sunny and 22C",
            "london": "Cloudy and 16C",
            "mumbai": "Humid and 31C",
        }
        return forecasts.get(normalized, f"Unknown forecast for {city}")

    return Agent(
        name="Weather Assistant",
        instructions=(
            "You are a weather assistant. "
            "If the user asks about weather, you must call `get_weather` exactly once "
            "before answering. Keep the final answer short."
        ),
        tools=[get_weather],
    )


adapter = OpenAIAgentsAdapter()


@agent_test(runs=3, agent_factory=build_weather_agent)
def test_openai_weather_agent(agent):
    result = adapter.run(agent, "What's the weather in Paris?")

    check = expect(result, collect=True)
    check.used_tool("get_weather")
    check.steps_less_than(8)
    check.final_output_contains("Paris")
    check.did_not_error()
    check.did_not_claim_confirmation_without_tool("get_weather")
    check.verify()
    return result


def build_research_agent():
    _require_openai_key()

    from agents import Agent, function_tool

    @function_tool
    def search_docs(query: str) -> str:
        """Search a small internal docs corpus and return concise notes."""
        normalized = query.strip().lower()
        if "invarium" in normalized:
            return (
                "Invarium supports repeated runs, behavioral assertions, "
                "baseline comparison, CLI commands, and pytest integration."
            )
        if "openai agents" in normalized:
            return (
                "OpenAI Agents SDK supports agents, tools, tracing, guardrails, "
                "and multi-agent workflows."
            )
        return "No matching notes found."

    @function_tool
    def summarize_notes(notes: str) -> str:
        """Summarize research notes into one short sentence."""
        if "No matching notes found." in notes:
            return "I could not find enough material to summarize."
        return (
            "Invarium focuses on behavioral testing with repeated runs, "
            "assertions, baselines, and pytest support."
        )

    return Agent(
        name="Research Assistant",
        instructions=(
            "You are a research assistant. "
            "When the user asks about Invarium, first call `search_docs` once. "
            "Then call `summarize_notes` once using the notes from `search_docs`. "
            "Do not answer before both tools are called. Keep the final answer to one sentence."
        ),
        tools=[search_docs, summarize_notes],
    )


@agent_test(runs=3, agent_factory=build_research_agent)
def test_openai_research_agent(agent):
    result = adapter.run(agent, "What does Invarium do?")

    check = expect(result, collect=True)
    check.used_tool("search_docs")
    check.used_tool("summarize_notes")
    check.used_tools_in_order(["search_docs", "summarize_notes"])
    check.steps_less_than(10)
    check.final_output_contains("Invarium")
    check.did_not_error()
    check.did_not_claim_confirmation_without_tool("summarize_notes")
    check.verify()
    return result
