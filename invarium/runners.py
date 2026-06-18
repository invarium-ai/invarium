from __future__ import annotations

from collections import defaultdict
from typing import Any

from .assertions import AssertionRecord, BehaviorAssertionError
from .report import TestRun, build_test_report, new_run_id, new_session_report
from .result import AgentResult
from .testing import AgentTestDefinition, resolve_test_argument


def run_single_test(definition: AgentTestDefinition) -> list[TestRun]:
    runs: list[TestRun] = []
    for _ in range(definition.runs):
        arguments, keyword_arguments = resolve_test_argument(definition)
        assertions: list[AssertionRecord] = []
        try:
            result = definition.func(*arguments, **keyword_arguments)
            if not isinstance(result, AgentResult):
                raise TypeError(
                    f"Test `{definition.name}` must return an AgentResult, got {type(result).__name__}."
                )
            run = TestRun(
                test_name=definition.name,
                run_id=new_run_id(),
                result=result,
                assertions=assertions,
                passed=True,
            )
        except BehaviorAssertionError as exc:
            assertions.extend(exc.records)
            run = TestRun(
                test_name=definition.name,
                run_id=new_run_id(),
                result=exc.result,
                assertions=assertions,
                passed=False,
                error=exc.record.message,
            )
        except Exception as exc:  # noqa: BLE001
            run = TestRun(
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
        runs.append(run)
    return runs


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
