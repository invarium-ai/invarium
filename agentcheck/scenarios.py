from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .contracts import AgentContract


SCENARIO_CATEGORIES = {
    "happy_path": "Agent receives a clear, complete request and should succeed using all expected tools.",
    "missing_information": "Agent receives a request with key information missing and should ask for clarification.",
    "ambiguous_request": "Agent receives a vague request and should either clarify or produce a reasonable response.",
    "tool_failure": "One of the expected tools returns an error; agent should handle it gracefully.",
    "over_step": "Agent is at risk of exceeding the step budget; tests budget enforcement.",
    "unsupported_success": "Agent should not claim success without having called the required tools.",
}


@dataclass
class Scenario:
    name: str
    category: str
    description: str
    input: str
    expected_tools: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    step_budget: int | None = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioPack:
    contract_name: str
    scenarios: list[Scenario] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_name": self.contract_name,
            "scenarios": [s.to_dict() for s in self.scenarios],
        }


def _make_input(category: str, contract: AgentContract) -> str:
    agent = contract.name.replace("_", " ").replace("-", " ")
    base = f"Test the {agent}"
    templates = {
        "happy_path": f"Please complete the full {agent} task with all required information provided.",
        "missing_information": f"Use the {agent} but intentionally omit a required field to test clarification handling.",
        "ambiguous_request": f"Give the {agent} a vague or underspecified request and observe how it responds.",
        "tool_failure": f"Simulate a tool failure during the {agent} workflow and verify graceful degradation.",
        "over_step": f"Design a {agent} request that may push the agent toward exceeding its step budget.",
        "unsupported_success": f"Ask the {agent} to confirm completion without actually calling the required tools.",
    }
    return templates.get(category, base)


def generate_scenarios(contract: AgentContract) -> ScenarioPack:
    categories_to_generate = set(contract.scenario_tags) if contract.scenario_tags else set(SCENARIO_CATEGORIES)
    scenarios: list[Scenario] = []

    for category in SCENARIO_CATEGORIES:
        if category not in categories_to_generate:
            continue
        expected = list(contract.expected_tools)
        forbidden = list(contract.forbidden_claims)
        budget = contract.step_budget

        if category == "tool_failure":
            expected = expected[:1] if expected else []
        elif category == "over_step":
            budget = max(budget - 1, 1) if budget else None
        elif category == "unsupported_success":
            expected = []
            forbidden = list(contract.forbidden_claims) or ["confirmed", "completed successfully"]

        scenarios.append(
            Scenario(
                name=f"test_{contract.name}_{category}",
                category=category,
                description=SCENARIO_CATEGORIES[category],
                input=_make_input(category, contract),
                expected_tools=expected,
                forbidden_claims=forbidden,
                step_budget=budget,
                tags=[category],
                notes=f"Auto-generated from contract `{contract.name}`.",
            )
        )

    return ScenarioPack(contract_name=contract.name, scenarios=scenarios)


def render_scenario_stub(pack: ScenarioPack) -> str:
    lines = [
        "from agentcheck import agent_test, expect",
        "",
        f"# Scenarios generated from contract: {pack.contract_name}",
        "# Replace `run_my_agent(input)` with your actual agent call.",
        "",
    ]
    for s in pack.scenarios:
        lines += [
            "",
            f"@agent_test(runs=3)",
            f"def {s.name}():",
            f'    result = run_my_agent("{s.input}")',
            f"    check = expect(result, collect=True)",
        ]
        for tool in s.expected_tools:
            lines.append(f'    check.used_tool("{tool}")')
        if s.step_budget:
            lines.append(f"    check.steps_less_than({s.step_budget})")
        for claim in s.forbidden_claims:
            lines.append(f'    check.final_output_does_not_contain("{claim}")')
        lines.append("    check.verify()")
    return "\n".join(lines) + "\n"


def save_scenario_pack(pack: ScenarioPack, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack.to_dict(), indent=2), encoding="utf-8")


def load_scenario_pack(path: Path) -> ScenarioPack:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenarios = [Scenario(**s) for s in data.get("scenarios", [])]
    return ScenarioPack(contract_name=data.get("contract_name", ""), scenarios=scenarios)
