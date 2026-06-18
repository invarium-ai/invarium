from __future__ import annotations

from dataclasses import dataclass

from invarium.adapters import OpenAIAgentsAdapter


@dataclass
class FakeToolItem:
    type: str
    raw_item: object
    output: dict | str | None = None
    status: str = "completed"
    created_at: str = "2026-04-27T00:00:00Z"


@dataclass
class FakeFunctionCallRawItem:
    call_id: str
    name: str
    arguments: str


@dataclass
class FakeFunctionCallOutputRawItem:
    call_id: str


@dataclass
class FakeMessageItem:
    type: str
    role: str
    content: str


@dataclass
class FakeRunResult:
    final_output: str
    new_items: list[object]
    usage: dict


def test_openai_agents_adapter_normalizes_tool_calls_and_messages():
    adapter = OpenAIAgentsAdapter()
    run_result = FakeRunResult(
        final_output="The weather in Paris is sunny.",
        new_items=[
            FakeMessageItem(type="message", role="assistant", content="Let me check."),
            FakeToolItem(
                type="function_call",
                raw_item=FakeFunctionCallRawItem(
                    call_id="call_123",
                    name="get_weather",
                    arguments='{"city": "Paris"}',
                ),
            ),
            FakeToolItem(
                type="tool_call_output_item",
                raw_item=FakeFunctionCallOutputRawItem(call_id="call_123"),
                output={"forecast": "sunny"},
            ),
            FakeMessageItem(
                type="message",
                role="assistant",
                content="The weather in Paris is sunny.",
            ),
        ],
        usage={"total_tokens": 42},
    )

    result = adapter.normalize("What's the weather in Paris?", run_result)

    assert result.final_output == "The weather in Paris is sunny."
    assert result.steps == 3
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "get_weather"
    assert result.tool_calls[0].args == {"city": "Paris"}
    assert result.tool_calls[0].output == {"forecast": "sunny"}
    assert result.messages[0]["role"] == "assistant"
    assert result.metadata["adapter"] == "openai_agents"
