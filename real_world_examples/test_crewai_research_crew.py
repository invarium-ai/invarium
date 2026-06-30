"""Behavioral contract for a real CrewAI research crew.

Makes live OpenAI calls through CrewAI. Run from the repo root with a key in `.env`:

    invarium test real_world_examples -k crew

The CrewAIAdapter surfaces each completed task as a step, so we assert that the
crew actually runs its tasks, finishes cleanly, and doesn't blow its step budget.
"""

from __future__ import annotations

from invarium import CrewAIAdapter, agent_test, expect

try:  # discovered from the repo root (cwd on sys.path)
    from real_world_examples.crewai_research_crew import build_research_crew
except ModuleNotFoundError:  # run with this folder as the working directory
    from crewai_research_crew import build_research_crew

adapter = CrewAIAdapter()


@agent_test(runs=2, agent_factory=build_research_crew)
def test_research_crew_completes_cleanly(crew):
    result = adapter.run(crew, "the benefits of automated testing in software")

    check = expect(result, collect=True)
    check.used_any_tool()          # each completed task shows up as a step
    check.finished_successfully()
    check.did_not_error()
    check.steps_less_than(6)
    check.verify()
    return result
