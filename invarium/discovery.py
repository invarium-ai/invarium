from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .testing import AgentTestDefinition


def discover_test_files(root: Path) -> list[Path]:
    patterns = ("test_*.py", "*_test.py")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(root.rglob(pattern))
    return sorted({path for path in files if ".invarium" not in path.parts})


def import_test_file(path: Path) -> None:
    project_root = str(Path.cwd())
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    module_name = "_invarium_" + "_".join(path.with_suffix("").parts)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not import test module from {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


def collect_registered_tests(filter_pattern: str | None = None) -> list[AgentTestDefinition]:
    from .testing import REGISTERED_TESTS

    tests = list(REGISTERED_TESTS)
    if filter_pattern:
        pattern = filter_pattern.lower()
        tests = [t for t in tests if pattern in t.name.lower()]
    return tests
