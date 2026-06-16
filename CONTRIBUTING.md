# Contributing to Invarium

Thanks for your interest in improving Invarium! This project is published on PyPI as
[`pygent-test`](https://pypi.org/project/pygent-test/) and ships the `agentcheck` command-line
tool. Contributions of all sizes are welcome — bug fixes, new adapters, assertions, examples,
and documentation.

## Getting Started

1. **Fork and clone** the repository.
2. **Create a virtual environment** and install the project with development extras:

   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. **Run the test suite** to confirm your environment is healthy:

   ```bash
   pytest tests -q
   ```

4. **Try the CLI** against the bundled examples:

   ```bash
   python -m agentcheck.cli test examples
   ```

## Finding Something to Work On

- Browse the [good first issues](https://github.com/invarium-ai/invarium/labels/good%20first%20issue)
  for newcomer-friendly tasks.
- Browse [help wanted](https://github.com/invarium-ai/invarium/labels/help%20wanted) for larger
  pieces such as new framework adapters.
- See the "Contributor-Friendly Areas" section of [ROADMAP.md](ROADMAP.md).

If you plan to work on something substantial, please open an issue first so we can discuss the
approach and avoid duplicate effort.

## Development Guidelines

- **Match the surrounding style.** Read nearby code before writing new code; keep naming,
  type hints, and comment density consistent.
- **Keep changes focused.** One logical change per pull request.
- **Add tests.** New assertions, adapters, or behaviors should come with unit tests under
  `tests/`. Use `pytest.importorskip(...)` for tests that depend on optional framework SDKs.
- **Update the docs.** If you add a public assertion, adapter, or CLI flag, update `README.md`
  (and the relevant guide) in the same PR.

### Writing a New Adapter

Adapters normalize a framework's run output into Invarium's `AgentResult` / `ToolCall` model.

1. Copy [`agentcheck/adapters/template.py`](agentcheck/adapters/template.py) as a starting point.
2. Lazy-import the framework SDK *inside* `run()` so importing `agentcheck.adapters` never
   requires optional dependencies (see `openai_agents.py` for the pattern).
3. Register the adapter in [`agentcheck/adapters/__init__.py`](agentcheck/adapters/__init__.py).
4. Add an optional dependency extra in `pyproject.toml`.
5. Add a unit test using a fake/mocked framework object.
6. Add the adapter to the table in `README.md`.

See [ADAPTER_GUIDE.md](ADAPTER_GUIDE.md) for a deeper walkthrough.

## Submitting a Pull Request

1. Create a branch off `main` (e.g. `feat/smolagents-adapter`).
2. Make your change, with tests and docs.
3. Ensure `pytest tests -q` passes.
4. Open a pull request describing **what** changed and **why**, and link any related issue.

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
