# Contributing

## Development setup

1. Use Python 3.11+.
2. Install dev dependencies:

```bash
uv sync --group dev
```

## Local quality checks

Run tests:

```bash
uv run python -m pytest -q
```

Run lint:

```bash
uv run ruff check .
```

Run formatting check (optional):

```bash
uv run ruff format --check .
```

Run type check:

```bash
uv run mypy
```

## Project layout

- Source code: `src/tomlstack/`
- Tests: `tests/`
- CI workflows: `.github/workflows/`

## Commit and PR guidelines

- Keep commits focused and minimal.
- Add or update tests for behavior changes.
- Update `CHANGELOG.md` for user-visible changes.
- Ensure CI is green before merge.

## Release flow

1. Bump version in `pyproject.toml`.
2. For release candidate, create tag like `v0.1.1rc1` and push.
3. For final release, create tag like `v0.1.1` and push.
4. CI workflows will run tests/build and publish automatically.

See `RELEASE.md` for full publishing details.
