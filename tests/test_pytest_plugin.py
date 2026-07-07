"""Regression tests for the pytest integration.

These run pytest in a subprocess against a throwaway project so they exercise
the *real*, entry-point-autoloaded plugin — the exact surface of the bug where
merely having Invarium installed interfered with a project's normal test
collection.
"""
from __future__ import annotations

import subprocess
import sys
from textwrap import dedent


def _run_pytest(target_dir):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(target_dir),
            "-p",
            "no:cacheprovider",
            "-q",
        ],
        capture_output=True,
        text=True,
    )


def test_installed_plugin_does_not_drop_normal_tests(tmp_path):
    """Having Invarium installed must not stop pytest collecting ordinary tests.

    The plugin is auto-loaded (pytest11 entry point) in *every* project once
    Invarium is installed, so a project that never uses ``@agent_test`` must see
    its plain ``def test_*`` functions, classes and parametrization collected
    exactly as if Invarium were not present.
    """
    (tmp_path / "test_plain.py").write_text(
        dedent(
            '''
            import pytest


            def test_a():
                assert 1 + 1 == 2


            def test_b():
                assert "x".upper() == "X"


            class TestGroup:
                def test_method(self):
                    assert sorted([2, 1]) == [1, 2]


            @pytest.mark.parametrize("n", [1, 2, 3])
            def test_param(n):
                assert n > 0
            '''
        ),
        encoding="utf-8",
    )

    result = _run_pytest(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "6 passed" in result.stdout, result.stdout + result.stderr


def test_invarium_and_normal_tests_coexist(tmp_path):
    """A file mixing plain pytest tests and @agent_test functions runs both."""
    (tmp_path / "test_mixed.py").write_text(
        dedent(
            '''
            from invarium import agent_test, AgentResult


            def test_plain_one():
                assert True


            def test_plain_two():
                assert 2 == 2


            @agent_test(runs=2)
            def test_agent_ok():
                return AgentResult(input="hi", final_output="done")
            '''
        ),
        encoding="utf-8",
    )

    result = _run_pytest(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    # two plain tests + one invarium item (which itself runs twice internally)
    assert "3 passed" in result.stdout, result.stdout + result.stderr
