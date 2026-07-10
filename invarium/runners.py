from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .assertions import AssertionRecord, BehaviorAssertionError
from .report import TestRun, build_test_report, new_run_id, new_session_report
from .result import AgentResult
from .testing import AgentTestDefinition, resolve_test_argument


def _execute_one_run(definition: AgentTestDefinition) -> TestRun:
    """Execute a single repetition of a test and capture it as a TestRun.

    All assertion/runtime failures are caught and turned into a failed TestRun so
    one bad run never aborts the others (important under concurrency).
    """
    arguments, keyword_arguments = resolve_test_argument(definition)
    assertions: list[AssertionRecord] = []
    try:
        result = definition.func(*arguments, **keyword_arguments)
        if not isinstance(result, AgentResult):
            raise TypeError(
                f"Test `{definition.name}` must return an AgentResult, got {type(result).__name__}."
            )
        return TestRun(
            test_name=definition.name,
            run_id=new_run_id(),
            result=result,
            assertions=assertions,
            passed=True,
        )
    except BehaviorAssertionError as exc:
        assertions.extend(exc.records)
        return TestRun(
            test_name=definition.name,
            run_id=new_run_id(),
            result=exc.result,
            assertions=assertions,
            passed=False,
            error=exc.record.message,
        )
    except Exception as exc:  # noqa: BLE001
        return TestRun(
            test_name=definition.name,
            run_id=new_run_id(),
            result=AgentResult(
                input="",
                final_output="",
                errors=[str(exc)],
                metadata={"exception_type": type(exc).__name__},
            ),
            assertions=assertions,
            passed=False,
            error=str(exc),
        )


def _should_parallelize(definition: AgentTestDefinition) -> bool:
    if definition.runs <= 1:
        return False
    if definition.parallel:
        return True
    return definition.max_workers is not None and definition.max_workers > 1


def _resolve_worker_count(definition: AgentTestDefinition) -> int:
    workers = definition.max_workers or definition.runs
    return max(1, min(workers, definition.runs))


def run_single_test(definition: AgentTestDefinition) -> list[TestRun]:
    total = definition.runs
    if total <= 0:
        return []
    if not _should_parallelize(definition):
        return [_execute_one_run(definition) for _ in range(total)]

    # Concurrent path: the `runs` repetitions are independent (each builds its own
    # agent via agent_factory), so run them on a thread pool. Adapters make blocking
    # I/O calls (invoke / run_sync / kickoff / HTTP) that release the GIL, so threads
    # give a near N-fold wall-clock win without an async rewrite. Results are stored
    # by submission index to keep run ordering deterministic in reports.
    workers = _resolve_worker_count(definition)
    results: list[TestRun | None] = [None] * total
    with ThreadPoolExecutor(
        max_workers=workers, thread_name_prefix=f"invarium-{definition.name}"
    ) as executor:
        futures = {executor.submit(_execute_one_run, definition): index for index in range(total)}
        for future, index in futures.items():
            results[index] = future.result()
    return [run for run in results if run is not None]


def run_test_suite(definitions: list[AgentTestDefinition]) -> tuple[list[dict[str, Any]], Any]:
    grouped_runs: dict[str, list[TestRun]] = defaultdict(list)
    for definition in definitions:
        for run in run_single_test(definition):
            grouped_runs[definition.name].append(run)
    reports = [build_test_report(name, runs) for name, runs in grouped_runs.items()]
    trace_payload = {
        "tests": {
            name: [run.to_dict() for run in runs]
            for name, runs in grouped_runs.items()
        }
    }
    return reports, new_session_report(reports), trace_payload
