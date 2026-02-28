# tomlstack

`tomlstack` is a lightweight TOML config loader for Python 3.11+ with:

- top-level `include` loading
- deterministic merge by include order
- `${path}` interpolation with cycle/undefined checks
- node-level provenance (`origin`, `explain`, `history`)

tomlstack does not try to be a configuration framework.
It address two missing pieces to TOML: file composition and safe interpolation — while keeping files self-contained and explainable.

## Install

```bash
pip install tomlstack
```

## Quick Start

`main.toml`:

```toml
include = [
    "./base.toml",
    "./prod.toml",
]

[db]
url = "postgres://${db.user}:${db.pass}@${db.host}:${db.port}"
```

`base.toml`:

```toml
[db]
user = "alice"
pass = "secret"
host = "localhost"
port = 5432
```

Python:

```python
from tomlstack import load

cfg = load("main.toml")
print(cfg["db"]["url"].raw)    # raw interpolation string
cfg.resolve()
print(cfg["db"]["url"].value)  # resolved value
print(cfg["db"]["url"].origin)
print(cfg["db"]["url"].history)
print(cfg.to_dict())
```

## Include Semantics

- top-level `include` only; nested `include` is treated as normal data
- syntax: string or list of strings
- valid include path forms:
- `./...` or `../...`
- `@label/...` (label from `__meta__.include.anchors`)
- absolute path
- any other form raises error with hint: `Use ./ or ../ or @label/`

### Meta Include Directives

```toml
[__meta__]
version = 1

[__meta__.include]
root = "../.."

[__meta__.include.anchors]
proj = "./shared"
```

- `__meta__.include.root` is sugar for `anchors.root`
- if both `root` and `anchors.root` exist and resolve differently, error
- anchor/root path values must be absolute or start with `./` or `../`
- if any file explicitly sets `__meta__.version`, all files in include chain must share one supported version (`1`)

## Merge Rules

Load order for current file:

1. merge first include
2. merge second include
3. ...
4. merge current file (highest priority)

Conflict behavior:

- dict: recursive merge, later wins on key conflict
- list: later value replaces whole list
- scalar: later value replaces earlier

## Interpolation Semantics

- interpolation happens on `cfg.resolve()`
- path syntax supports dot and list index: `${db.apps[0]}`
- full-string interpolation (`"${db.port}"`) keeps source type
- embedded interpolation (`"postgres://${db.host}:${db.port}"`) allows only:
- `str`, `int`, `float`, `date`, `time`, `datetime`
- formatting syntax: `${path:spec}`
- for `date/time/datetime`, formatting uses `strftime`
- otherwise uses Python `format(value, spec)`
- undefined reference raises `InterpolationUndefinedError`
- interpolation cycle raises `InterpolationCycleError`

## Public API

- `cfg = load("f.toml")`
- `cfg.resolve()`
- `cfg.to_dict()`
- `node = cfg["proj"][0]["path"]["foo"]`
- `node.raw`
- `node.value`
- `node.origin`
- `node.history`
- `node.preview()`
- `cfg.to_toml()` -> `NotImplementedError`

## Current Limitations

- interpolation path parser supports unquoted dot keys and numeric list indices
- no nested interpolation expressions
- `to_toml()` is not implemented yet

## TODO

- [ ] review the details of interpolation
- [ ] explain history with interpolation

## Release To PyPI

Build package:

```bash
uv run --with build python -m build
```

Upload to TestPyPI first:

```bash
uv run --with twine python -m twine upload --repository testpypi dist/*
```

Verify install from TestPyPI:

```bash
python -m pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple tomlstack
```

Upload to PyPI:

```bash
uv run --with twine python -m twine upload dist/*
```
