from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


CONTRACT_SCHEMA_VERSION = "1"

CONTRACT_FILE = "agent_contract.json"

VALID_SCENARIO_TAGS = {
    "happy_path",
    "missing_information",
    "ambiguous_request",
    "tool_failure",
    "over_step",
    "unsupported_success",
    "regression",
    "edge_case",
}


@dataclass
class AgentContract:
    name: str
    description: str = ""
    schema_version: str = CONTRACT_SCHEMA_VERSION
    expected_tools: list[str] = field(default_factory=list)
    required_tool_order: list[str] = field(default_factory=list)
    step_budget: int | None = None
    success_conditions: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    scenario_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentContract":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            schema_version=data.get("schema_version", CONTRACT_SCHEMA_VERSION),
            expected_tools=data.get("expected_tools", []),
            required_tool_order=data.get("required_tool_order", []),
            step_budget=data.get("step_budget"),
            success_conditions=data.get("success_conditions", []),
            forbidden_claims=data.get("forbidden_claims", []),
            scenario_tags=data.get("scenario_tags", []),
        )


@dataclass
class ContractValidationError:
    field: str
    message: str


def _default_contract(name: str = "my_agent") -> AgentContract:
    return AgentContract(
        name=name,
        description="Describe what this agent is supposed to do.",
        expected_tools=["search", "summarize"],
        required_tool_order=[],
        step_budget=10,
        success_conditions=["answer provided", "no error"],
        forbidden_claims=["reservation complete", "booked"],
        scenario_tags=["happy_path"],
    )


def validate_contract(contract: AgentContract) -> list[ContractValidationError]:
    errors: list[ContractValidationError] = []

    if not contract.name or not contract.name.strip():
        errors.append(ContractValidationError("name", "Contract name must not be empty."))
    elif not contract.name.replace("_", "").replace("-", "").isalnum():
        errors.append(
            ContractValidationError(
                "name",
                f"Contract name `{contract.name}` should use only letters, digits, hyphens, or underscores.",
            )
        )

    if contract.schema_version != CONTRACT_SCHEMA_VERSION:
        errors.append(
            ContractValidationError(
                "schema_version",
                f"Unsupported schema version `{contract.schema_version}`. Expected `{CONTRACT_SCHEMA_VERSION}`.",
            )
        )

    if contract.step_budget is not None and contract.step_budget < 1:
        errors.append(ContractValidationError("step_budget", "step_budget must be a positive integer."))

    for tag in contract.scenario_tags:
        if tag not in VALID_SCENARIO_TAGS:
            errors.append(
                ContractValidationError(
                    "scenario_tags",
                    f"Unknown scenario tag `{tag}`. Valid tags: {sorted(VALID_SCENARIO_TAGS)}.",
                )
            )

    if contract.required_tool_order:
        unknown = set(contract.required_tool_order) - set(contract.expected_tools)
        if unknown:
            errors.append(
                ContractValidationError(
                    "required_tool_order",
                    f"required_tool_order references tools not in expected_tools: {sorted(unknown)}.",
                )
            )

    return errors


def load_contract(path: Path) -> AgentContract:
    data = json.loads(path.read_text(encoding="utf-8"))
    return AgentContract.from_dict(data)


def save_contract(contract: AgentContract, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract.to_dict(), indent=2), encoding="utf-8")
