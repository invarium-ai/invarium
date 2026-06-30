"""A real CrewAI research crew — a multi-agent pattern lots of teams ship.

A Researcher agent gathers facts and a Writer agent summarizes them, run as a
sequential CrewAI process backed by a real OpenAI model (via CrewAI's litellm
layer). No mocks.

Note on what Invarium observes here: the ``CrewAIAdapter`` normalizes each crew
*task* into a step, so the behavioral contract is about the crew completing its
tasks and finishing cleanly — not individual sub-tool calls. Keys are read from
the repo-root ``.env`` (gitignored).
"""

from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))


def _require_openai_key() -> str:
    value = os.environ.get("OPENAI_API_KEY", "").strip()
    if not value or "REPLACE" in value:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add your real key to the repo-root `.env` "
            "(see real_world_examples/README.md)."
        )
    return value


def build_research_crew():
    _require_openai_key()

    from crewai import Agent, Crew, LLM, Process, Task

    llm = LLM(model=os.environ.get("RW_OPENAI_MODEL", "gpt-4o-mini"), temperature=0)

    researcher = Agent(
        role="Senior Researcher",
        goal="Find accurate, concise key facts about {query}",
        backstory="You research topics carefully and report only well-supported facts.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    writer = Agent(
        role="Technical Writer",
        goal="Turn research notes into a short, clear summary",
        backstory="You write tight, accurate two-sentence summaries for busy readers.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    research_task = Task(
        description="Research the topic: {query}. List three concise, factual bullet points.",
        expected_output="Three factual bullet points.",
        agent=researcher,
    )
    write_task = Task(
        description="Using the research notes, write a two-sentence summary about {query}.",
        expected_output="A two-sentence summary.",
        agent=writer,
        context=[research_task],
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        process=Process.sequential,
        verbose=False,
    )
