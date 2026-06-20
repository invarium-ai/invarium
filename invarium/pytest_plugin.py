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
        return self.path, 0, f"invarium: {self.definition.name}"


class InvariumFile(pytest.Module):
    def collect(self):
        module = self._getobj()
        for name in dir(module):
            obj = getattr(module, name)
            definition = getattr(obj, "__invarium_test__", None)
            if definition is None:
                continue
            yield InvariumItem.from_parent(
                self,
                name=definition.name,
                definition=definition,
            )


def pytest_collect_file(file_path, parent):  # noqa: ANN001
    if file_path.suffix != ".py":
        return None
    if not (file_path.name.startswith("test_") or file_path.name.endswith("_test.py")):
        return None
    return InvariumFile.from_parent(parent, path=file_path)


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
