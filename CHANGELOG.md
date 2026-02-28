# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project follows Semantic Versioning.

## [Unreleased]

### Added

- CI Python version matrix (`3.11`, `3.12`, `3.13`, `3.x`).
- Development tool configuration for `ruff`, `mypy`, and `pytest`.
- Publishing workflows for TestPyPI and PyPI with GitHub Release automation.

## [0.1.1rc1] - 2026-02-28

### Added

- First release candidate published to TestPyPI.

## [0.1.0] - 2026-02-28

### Added

- Initial public release of `tomlstack`.
- Top-level `include` support with deterministic merge behavior.
- `${path}` interpolation with cycle and undefined reference checks.
- Node provenance (`origin`, `history`, `explain`) APIs.
