# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project follows Semantic Versioning.

## [0.2.0] - 2026-06-24

### Added

- Include-tree inspection through `cfg.include_tree`.
- Node provenance and interpolation dependency inspection through `TomlNode`.
- Specific errors for invalid TOML, undefined interpolation references, and
  interpolation cycles.

### Changed

- Configuration loading now binds each value to its source history internally,
  making merge and interpolation provenance consistent.
- `TomlNode` is the public node-query type; nodes and `TomlStack` instances are
  created through configuration loading and navigation only.

### Removed

- `TomlStack.view`; use `cfg.raw` for unexpanded data or `cfg.to_dict()` for a
  resolved snapshot.
- `TomlStack.to_dict(resolve=False)`; use `cfg.raw`.
- `TomlHist` and `TomlFile.str_`; history now contains `TomlFile` values with
  `reference` and resolved `path` fields.
- Legacy metadata/version directives and their associated error classes.

## [0.1.2] - 2026-03-01

- first publish version

## [0.1.1rc3] - 2026-03-01

- try to fix OIDC

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
