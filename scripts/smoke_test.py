from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_step(label: str, command: list[str], *, optional: bool = False) -> bool:
    print(f"\n== {label} ==")
    print(" ".join(command))
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode == 0:
        print(f"[PASS] {label}")
        return True
    if optional:
        print(f"[SKIP] {label} failed with exit code {completed.returncode}")
        return False
    print(f"[FAIL] {label} failed with exit code {completed.returncode}")
    raise SystemExit(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a quick smoke test for the installed Invarium package."
    )
    parser.add_argument(
        "--with-live",
        action="store_true",
        help="Also run the live OpenAI integration tests. Requires OPENAI_API_KEY.",
    )
    args = parser.parse_args()

    python = sys.executable

    run_step(
        "Import package",
        [python, "-c", "import invarium; print(invarium.__all__)"],
    )
    run_step(
        "CLI help",
        [python, "-m", "invarium.cli", "--help"],
    )
    if importlib.util.find_spec("pytest") is None:
        print("\n[SKIP] Unit tests skipped because `pytest` is not installed in this environment.")
    else:
        run_step(
            "Unit tests",
            [python, "-m", "pytest", "tests", "-q"],
        )
    run_step(
        "Passing demo",
        [python, "-m", "invarium.cli", "test", "examples"],
    )
    if importlib.util.find_spec("langgraph") is None or importlib.util.find_spec("langchain_core") is None:
        print("\n[SKIP] LangGraph example skipped because `langgraph` or `langchain-core` is not installed.")
    else:
        run_step(
            "LangGraph example",
            [python, "-m", "invarium.cli", "test", "framework_examples"],
        )
    run_step(
        "Bless passing demo baseline",
        [python, "-m", "invarium.cli", "bless", "examples"],
    )
    run_step(
        "Broken behavior demo",
        [python, "-m", "invarium.cli", "test", "regression_examples"],
        optional=True,
    )

    if args.with_live:
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            print("\n[SKIP] Live integration tests requested, but OPENAI_API_KEY is not set.")
        else:
            run_step(
                "Live OpenAI integration tests",
                [python, "-m", "invarium.cli", "test", "integration_examples"],
            )

    print("\nSmoke test completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
