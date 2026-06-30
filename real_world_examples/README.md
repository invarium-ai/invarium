# Real-world agent examples (live LLM calls)

Behavioral contracts run against **real agents people actually ship** — not mocks.
These make live LLM and web-search calls, so they need API keys and they cost a few
fractions of a cent per run.

| Test | Agent | Framework | Behavior under test |
|---|---|---|---|
| `test_langgraph_search_agent.py` | ReAct search+calculator agent | LangGraph `create_react_agent` + OpenAI/Gemini + Tavily | grounds factual answers in a real web search; uses the calculator for math; no runaway search loops |
| `test_openai_support_agent.py` | Support / refund agent | OpenAI Agents SDK | verifies the order before refunding; never claims a refund without calling the refund tool |
| `test_crewai_research_crew.py` | Researcher + Writer crew | CrewAI | a multi-agent sequential crew runs its tasks and finishes cleanly within a step budget |

## Setup

Put your keys in the repo-root `.env` (already gitignored — never committed):

```
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...      # for the Gemini variant
GEMINI_API_KEY=...      # alias, same value
TAVILY_API_KEY=tvly-...
```

Install the connectors:

```bash
pip install langchain-openai langchain-google-genai langchain-tavily openai-agents crewai
```

## Run

From the repo root:

```bash
invarium test real_world_examples                 # both agents, repeated runs
invarium test real_world_examples -k search       # just the LangGraph search agent
invarium test real_world_examples -k refund       # just the OpenAI refund agent
```

## Swap the model to catch real behavioral drift

The search agent's provider/model are environment-driven, so you can bless one
configuration and compare another — real model behavior, no mocks:

```bash
# bless a known-good baseline (OpenAI gpt-4o-mini)
invarium bless real_world_examples

# does a cheaper/older model still ground its answers with search?
RW_OPENAI_MODEL=gpt-3.5-turbo invarium test real_world_examples -k search

# or switch provider entirely
RW_LLM_PROVIDER=gemini invarium test real_world_examples -k search

# relax the system prompt and see whether the agent still grounds with search
RW_WEAK_PROMPT=1 invarium test real_world_examples -k grounds
```

> Honest note from live runs: on the "current CEO of OpenAI" question, both
> `gpt-4o-mini` and `gpt-3.5-turbo` keep calling `tavily_search` even under the
> relaxed prompt — well-aligned models are cautious about time-sensitive facts, so
> no regression appears. `RW_WEAK_PROMPT=1` reliably induces a dropped-search
> regression on *stable* facts the model is confident it already knows (e.g.
> "Who wrote Hamlet?"). The point of Invarium is exactly this: you find out which
> case you're in from the behavior, not from guessing.

Because these are live, non-deterministic agents, the `runs=N` repetition and
flakiness score matter: a single pass doesn't prove the behavior is stable.

> CI note: these live tests are intentionally **not** part of the unit suite
> (`pytest tests`). They require secrets and a network, so run them on demand.
