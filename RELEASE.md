# Release Guide

This project uses `hatchling` + `hatch-vcs` via `pyproject.toml`.

## GitHub Actions automation

- Push/PR to `main`: run tests and build only (no upload).
- Tag `vX.Y.ZrcN`: run tests, build, check, then upload to TestPyPI.
- Tag `vX.Y.Z`: run tests, build, check, upload to PyPI, and create GitHub Release.

Workflows:

- `.github/workflows/ci.yml`
- `.github/workflows/publish-testpypi.yml`
- `.github/workflows/publish-pypi.yml`

For publishing workflows in this repo, configure PyPI and TestPyPI Trusted Publisher:

- Owner: `WXZhao7`
- Repository: `tomlstack`
- Workflow file:
  - TestPyPI: `.github/workflows/publish-testpypi.yml`
  - PyPI: `.github/workflows/publish-pypi.yml`
- Environment name: leave empty (not used by workflows)

## 1) Create release tag

Version is derived from git tags (`hatch-vcs`), not hardcoded in `pyproject.toml`.

- Release candidate: `vX.Y.ZrcN` (example: `v0.1.1rc1`)
- Final release: `vX.Y.Z` (example: `v0.1.1`)

```bash
git tag v0.1.1rc1
git push origin v0.1.1rc1
```

## 2) Clean old artifacts

```bash
rm -rf dist/
```

## 3) Build package

```bash
uv run --with build python -m build
```

## 4) Validate metadata

```bash
uv run --with twine python -m twine check dist/*
```

## 5) Upload to TestPyPI

```bash
uv run --with twine python -m twine upload --repository testpypi dist/*
```

## 6) Test installation from TestPyPI

```bash
python -m pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple tomlstack
python -c "import tomlstack; print(tomlstack.__all__)"
```

## 7) Upload to PyPI

```bash
uv run --with twine python -m twine upload dist/*
```

## 8) Final release tag

```bash
git tag v0.1.1
git push origin v0.1.1
```
