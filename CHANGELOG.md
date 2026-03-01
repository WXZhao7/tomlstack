# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project follows Semantic Versioning.

## [0.1.1rc2] - 2026-03-01

### Added

- CI Python version matrix (`3.11`, `3.12`, `3.13`, `3.x`).
- Development tool configuration for `ruff`, `mypy`, and `pytest`.
- Publishing workflows for TestPyPI and PyPI with GitHub Release automation.

### Changed

- Packaging version now comes from git tags via `hatch-vcs`.
- CI now produces coverage reports and enforces a coverage threshold.

## [0.1.1rc1] - 2026-02-28

### Added

- First release candidate published to TestPyPI.

## [0.1.0] - 2026-02-28

### Added

- Initial public release of `tomlstack`.
- Top-level `include` support with deterministic merge behavior.
- `${path}` interpolation with cycle and undefined reference checks.
- Node provenance (`origin`, `history`, `explain`) APIs.
