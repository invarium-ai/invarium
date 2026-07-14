"""Tests for opt-in parallel execution of ``runs=N`` repetitions."""
from __future__ import annotations

import threading
import time

import pytest
from invarium import AgentResult, ToolCall, agent_test
from invarium.runners import run_single_test
from invarium.testing import REGISTERED_TESTS, AgentTestDefinition


def _ok_result() -> AgentResult:
    return AgentResult(input="x", final_output="done", tool_calls=[ToolCall(name="search")])


def test_agent_test_stores_parallel_params():
    @agent_test(runs=3, parallel=True, max_workers=4)
    def sample():
        return _ok_result()

    definition = sample.__invarium_test__
    try:
        assert definition.parallel is True
        assert definition.max_workers == 4
    finally:
        REGISTERED_TESTS.remove(definition)  # don't leak into the global registry


def test_invalid_max_workers_raises():
    with pytest.raises(ValueError):
        @agent_test(runs=2, max_workers=0)
        def _bad():
            return _ok_result()


def test_parallel_runs_execute_concurrently():
    """Deterministic proof: a barrier that only releases when all N run at once.

    If the runs were serialized, the first ``wait()`` would block alone and trip
    the barrier timeout, turning every run into a failure.
    """
    barrier = threading.Barrier(3, timeout=10)

    def agent_fn():
        barrier.wait()
        return _ok_result()

    definition = AgentTestDefinition(func=agent_fn, name="test_conc", runs=3, parallel=True)
    runs = run_single_test(definition)

    assert len(runs) == 3
    assert all(run.passed for run in runs), [run.error for run in runs]


def test_sequential_runs_do_not_overlap():
    """Mirror image: with the default (sequential), the same barrier never fills."""
    barrier = threading.Barrier(3, timeout=0.5)

    def agent_fn():
        barrier.wait()
        return _ok_result()

    definition = AgentTestDefinition(func=agent_fn, name="test_seq", runs=3, parallel=False)
    runs = run_single_test(definition)

    assert len(runs) == 3
    assert all(not run.passed for run in runs)


def test_parallel_matches_sequential_results():
    def build(parallel: bool) -> AgentTestDefinition:
        return AgentTestDefinition(
            func=_ok_result, name="test_eq", runs=5, parallel=parallel
        )

    sequential = run_single_test(build(False))
    parallel = run_single_test(build(True))

    assert len(sequential) == len(parallel) == 5
    assert all(run.passed for run in sequential + parallel)


def test_max_workers_activates_parallel_and_caps_concurrency():
    """max_workers > 1 turns on parallelism even when parallel is not set, and it
    never runs more than max_workers at once."""
    lock = threading.Lock()
    active = 0
    peak = 0

    def agent_fn():
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.1)
        with lock:
            active -= 1
        return _ok_result()

    definition = AgentTestDefinition(
        func=agent_fn, name="test_cap", runs=6, parallel=False, max_workers=2
    )
    runs = run_single_test(definition)

    assert len(runs) == 6
    assert all(run.passed for run in runs)
    assert peak == 2  # it parallelized (>1) but never exceeded the cap (<=2)


def test_single_run_never_parallelizes():
    definition = AgentTestDefinition(func=_ok_result, name="test_one", runs=1, parallel=True)
    runs = run_single_test(definition)
    assert len(runs) == 1 and runs[0].passed


def test_failure_in_one_parallel_run_is_isolated():
    """A failing run must be captured, not crash the whole batch."""
    counter = {"n": 0}
    lock = threading.Lock()

    def agent_fn():
        with lock:
            counter["n"] += 1
            n = counter["n"]
        if n == 1:
            raise RuntimeError("boom")
        return _ok_result()

    definition = AgentTestDefinition(func=agent_fn, name="test_iso", runs=4, parallel=True)
    runs = run_single_test(definition)

    assert len(runs) == 4
    assert sum(1 for run in runs if not run.passed) == 1
    assert sum(1 for run in runs if run.passed) == 3
