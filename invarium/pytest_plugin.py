from __future__ import annotations

from dataclasses import dataclass

import pytest

from .report import build_test_report
from .runners import run_single_test
from .testing import AgentTestDefinition


@dataclass(slots=True)
class InvariumRunResult:
    report_text: str


class InvariumItem(pytest.Item):
    def __init__(self, *, definition: AgentTestDefinition, **kwargs):
        super().__init__(**kwargs)
        self.definition = definition

    def runtest(self) -> None:
        runs = run_single_test(self.definition)
        report = build_test_report(self.definition.name, runs)
        if report.failed_runs:
            raise AssertionError(_format_failure_report(report))

    def repr_failure(self, excinfo, style=None):  # noqa: ANN001
        if excinfo.errisinstance(AssertionError):
            return str(excinfo.value)
        return super().repr_failure(excinfo, style=style)

    def reportinfo(self):
        # ``Node.path`` (pathlib) was added in pytest 7.0; fall back to the
        # deprecated ``fspath`` on pytest 6.x so the plugin stays compatible.
        location = getattr(self, "path", None)
        if location is None:
            location = self.fspath
        return location, 0, f"invarium: {self.definition.name}"


@pytest.hookimpl(tryfirst=True)
def pytest_pycollect_makeitem(collector, name, obj):  # noqa: ANN001
    """Turn ``@agent_test`` functions into Invarium items during normal collection.

    We deliberately hook at the *item* level (``pytest_pycollect_makeitem``)
    rather than claiming whole files (``pytest_collect_file``). This is the key
    to being a well-behaved, globally auto-loaded plugin:

    * The builtin ``Module`` collector still owns every ``test_*.py`` file, so
      ordinary ``def test_*`` functions, classes, fixtures and parametrization
      are collected exactly as they would be without Invarium installed.
    * Only objects carrying ``__invarium_test__`` (set by :func:`agent_test`)
      are converted into :class:`InvariumItem`. Everything else returns ``None``
      and flows through pytest's default collection untouched.

    An earlier version returned a custom ``pytest.Module`` subclass from
    ``pytest_collect_file`` for *every* matching file. That hijacked collection
    of files Invarium had no business touching and made an installed-but-unused
    Invarium silently interfere with a project's normal test suite.
    ``pytest_pycollect_makeitem`` also has a stable signature across pytest
    6.x-9.x, unlike ``pytest_collect_file`` whose parameter was renamed
    (``path`` -> ``file_path``) in pytest 7.0.
    """
    definition = getattr(obj, "__invarium_test__", None)
    if definition is None:
        return None
    return InvariumItem.from_parent(
        collector,
        name=definition.name,
        definition=definition,
    )


def _format_failure_report(report) -> str:  # noqa: ANN001
    lines = [
        f"Invarium failed: {report.test_name}",
        f"Runs: {report.total_runs}",
        f"Passed: {report.passed_runs}",
        f"Failed: {report.failed_runs}",
        f"Success rate: {report.success_rate:.1f}%",
        f"Average steps: {report.average_steps:.1f}",
    ]
    if report.failure_reasons:
        lines.append("")
        lines.append("Failures:")
        for reason in report.failure_reasons:
            lines.append(f"- {reason}")
    return "\n".join(lines)
