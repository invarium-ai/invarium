# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Rebranded to **Invarium** (published on PyPI as `pygent-test`, CLI `agentcheck`).
- Refreshed README and contributor documentation.

### Added
- Contributing guide, code of conduct, security policy, and issue/PR templates.
- Continuous integration running the test suite on Python 3.10–3.13.

## [0.3.1]

### Added
- `tool_called_with_args` assertion for checking tool arguments.
- Shareable baselines.

## [0.3.0]

### Added
- `AdapterConfig` support in the config file.
- Full set of framework adapters: OpenAI Agents, LangGraph, CrewAI, HTTP, and Python.

## [0.2.0]

### Added
- HTTP and CrewAI adapter coverage.
- Expanded reports and regression analysis.

## [0.1.0]

### Added
- Initial release: repeated-run behavioral tests, core assertions, baselines, regression
  detection, and local JSON/Markdown/HTML reports.
