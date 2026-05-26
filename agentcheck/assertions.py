from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .result import AgentResult


FAILURE_CATEGORIES = {
    "missing_required_tool",
    "wrong_tool_order",
    "step_budget_exceeded",
    "unsupported_success_claim",
    "runtime_error",
    "output_mismatch",
    "unexpected_error",
    "tool_failure",
    "latency_exceeded",
    "cost_exceeded",
}


@dataclass(slots=True)
class AssertionRecord:
    name: str
    passed: bool
    message: str
    category: str | None = None


class BehaviorAssertionError(AssertionError):
    def __init__(self, records: list[AssertionRecord], result: AgentResult):
        message = "\n".join(record.message for record in records if not record.passed) or "Behavior assertion failed."
        super().__init__(message)
        self.records = records
        self.record = next((record for record in records if not record.passed), records[0])
        self.result = result


class Expectation:
    def __init__(self, result: AgentResult, *, collect: bool = False):
        self.result = result
        self.collect = collect
        self.records: list[AssertionRecord] = []

    def _tool_names(self) -> list[str]:
        return [tool.name for tool in self.result.tool_calls]

    def _tool_count(self, tool_name: str) -> int:
        return self._tool_names().count(tool_name)

    def _check(self, name: str, passed: bool, success_message: str, failure_message: str, category: str | None = None) -> "Expectation":
        record = AssertionRecord(
            name=name,
            passed=passed,
            message=success_message if passed else failure_message,
            category=category if not passed else None,
        )
        self.records.append(record)
        if not passed and not self.collect:
            raise BehaviorAssertionError([record], self.result)
        return self

    def verify(self) -> AgentResult:
        failures = [record for record in self.records if not record.passed]
        if failures:
            raise BehaviorAssertionError(self.records, self.result)
        return self.result

    def used_tool(self, tool_name: str) -> "Expectation":
        names = self._tool_names()
        return self._check(
            "used_tool",
            tool_name in names,
            f"Observed tool `{tool_name}`.",
            f"Expected tool `{tool_name}` to be called, but saw {names or 'no tools'}.",
            category="missing_required_tool",
        )

    def used_tool_times(self, tool_name: str, count: int) -> "Expectation":
        actual = self._tool_count(tool_name)
        return self._check(
            "used_tool_times",
            actual == count,
            f"Tool `{tool_name}` was used exactly {count} time(s).",
            f"Expected tool `{tool_name}` to be used exactly {count} time(s), but saw {actual}.",
            category="missing_required_tool",
        )

    def used_tool_at_least(self, tool_name: str, count: int) -> "Expectation":
        actual = self._tool_count(tool_name)
        return self._check(
            "used_tool_at_least",
            actual >= count,
            f"Tool `{tool_name}` was used at least {count} time(s).",
            f"Expected tool `{tool_name}` to be used at least {count} time(s), but saw {actual}.",
            category="missing_required_tool",
        )

    def used_tool_at_most(self, tool_name: str, count: int) -> "Expectation":
        actual = self._tool_count(tool_name)
        return self._check(
            "used_tool_at_most",
            actual <= count,
            f"Tool `{tool_name}` was used at most {count} time(s).",
            f"Expected tool `{tool_name}` to be used at most {count} time(s), but saw {actual}.",
            category="missing_required_tool",
        )

    def did_not_use_tool(self, tool_name: str) -> "Expectation":
        names = self._tool_names()
        return self._check(
            "did_not_use_tool",
            tool_name not in names,
            f"Tool `{tool_name}` was not used.",
            f"Expected tool `{tool_name}` to be avoided, but it was called.",
            category="missing_required_tool",
        )

    def used_tools_in_order(self, tool_names: Iterable[str]) -> "Expectation":
        ordered = list(tool_names)
        seen = self._tool_names()
        position = 0
        for name in seen:
            if position < len(ordered) and name == ordered[position]:
                position += 1
        return self._check(
            "used_tools_in_order",
            position == len(ordered),
            f"Observed tools in order {ordered}.",
            f"Expected tools in order {ordered}, but saw {seen or 'no tools'}.",
            category="wrong_tool_order",
        )

    def steps_less_than(self, limit: int) -> "Expectation":
        return self._check(
            "steps_less_than",
            self.result.steps < limit,
            f"Completed in {self.result.steps} steps, below limit {limit}.",
            f"Expected fewer than {limit} steps, but saw {self.result.steps}.",
            category="step_budget_exceeded",
        )

    def finished_successfully(self) -> "Expectation":
        return self._check(
            "finished_successfully",
            not self.result.errors and bool(self.result.final_output.strip()),
            "Run finished successfully.",
            "Expected a successful finish, but errors were present or final output was empty.",
            category="runtime_error",
        )

    def did_not_error(self) -> "Expectation":
        return self._check(
            "did_not_error",
            not self.result.errors,
            "Run completed without errors.",
            f"Expected no errors, but saw: {self.result.errors}.",
            category="runtime_error",
        )

    def final_output_contains(self, text: str) -> "Expectation":
        return self._check(
            "final_output_contains",
            text in self.result.final_output,
            f"Final output contained `{text}`.",
            f"Expected final output to contain `{text}`.",
            category="output_mismatch",
        )

    def final_output_does_not_contain(self, text: str) -> "Expectation":
        return self._check(
            "final_output_does_not_contain",
            text not in self.result.final_output,
            f"Final output did not contain `{text}`.",
            f"Expected final output to avoid `{text}`.",
            category="output_mismatch",
        )

    def did_not_claim_confirmation_without_tool(self, required_tool: str | None = None) -> "Expectation":
        confirmation_phrases = (
            "booked",
            "confirmed",
            "reservation complete",
            "refund issued",
            "completed successfully",
        )
        final_output = self.result.final_output.lower()
        claims_success = any(phrase in final_output for phrase in confirmation_phrases)
        successful_tools = [tool.name for tool in self.result.tool_calls if tool.success]
        tool_to_check = required_tool
        if tool_to_check is None and successful_tools:
            tool_to_check = successful_tools[-1]
        has_supporting_tool = bool(tool_to_check and tool_to_check in successful_tools)
        passed = not claims_success or has_supporting_tool
        detail = tool_to_check or "a successful tool call"
        return self._check(
            "did_not_claim_confirmation_without_tool",
            passed,
            "No unsupported confirmation claim detected.",
            f"Agent claimed success in final output without evidence from {detail}.",
            category="unsupported_success_claim",
        )

    def used_any_tool(self) -> "Expectation":
        names = self._tool_names()
        return self._check(
            "used_any_tool",
            bool(names),
            f"Agent used {len(names)} tool(s).",
            "Expected agent to use at least one tool, but none were called.",
            category="missing_required_tool",
        )

    def final_output_matches_pattern(self, pattern: str) -> "Expectation":
        matched = bool(re.search(pattern, self.result.final_output))
        return self._check(
            "final_output_matches_pattern",
            matched,
            f"Final output matched pattern `{pattern}`.",
            f"Expected final output to match pattern `{pattern}`.",
            category="output_mismatch",
        )

    def tool_succeeded(self, tool_name: str) -> "Expectation":
        successful = [tool.name for tool in self.result.tool_calls if tool.success]
        return self._check(
            "tool_succeeded",
            tool_name in successful,
            f"Tool `{tool_name}` completed successfully.",
            f"Expected tool `{tool_name}` to succeed, but it was not found among successful calls {successful or 'none'}.",
            category="tool_failure",
        )


def expect(result: AgentResult, *, collect: bool = False) -> Expectation:
    return Expectation(result, collect=collect)
