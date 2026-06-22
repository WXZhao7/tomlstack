# tomlstack

`tomlstack` is a lightweight TOML config loader for Python 3.11+ with:

- top-level `include` loading
- deterministic merge by include order
- `${path}` interpolation with cycle/undefined checks
- node-level provenance (`origin`, `history`)

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
print(cfg["db"]["url"].value)  # resolved value
print(cfg["db"]["url"].origin)
print(cfg["db"]["url"].history)
print(cfg.raw)                   # raw configuration snapshot
print(cfg.resolved)              # resolved configuration snapshot
```

## Include Semantics

- top-level `include` only; nested `include` is treated as normal data
- syntax: string or list of strings
- valid include path forms:
  - `./...` or `../...`
  - `@label/...` (label from `tomlstack.anchors`)
  - absolute path
- any other form raises an error with a path-format hint

### Meta Include Directives

```toml
[tomlstack.anchors]
proj = "./shared"
```

- anchors are local to the file that declares them
- anchor path values must be absolute or start with `./` or `../`

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

- interpolation is resolved lazily by `cfg.resolve()`, `cfg.to_dict()`,
  `cfg.resolved`, or `node.value`
- path syntax supports dot and list index: `${db.apps[0]}`
- full-string interpolation (`"${db.port}"`) keeps source type
- embedded interpolation (`"postgres://${db.host}:${db.port}"`) allows only:
- `str`, `int`, `float`, `date`, `time`, `datetime`
- formatting syntax: `${path:spec}`
- for `date/time/datetime`, formatting uses `strftime`
- otherwise uses Python `format(value, spec)`
- invalid paths, undefined references, and cycles raise `InterpolationError`

## Public API

- `cfg = load("f.toml")`
- `cfg.raw` — raw configuration snapshot
- `cfg.resolved` — resolved configuration snapshot
- `cfg.resolve()`
- `cfg.to_dict()` — equivalent to `cfg.resolved`
- `node = cfg["proj"][0]["path"]["foo"]`
- `node.raw`
- `node.value`
- `node.origin`
- `node.history`
- `node.preview()`
- `cfg.to_toml()` -> `NotImplementedError`

`cfg.raw`, `cfg.resolved`, `cfg.to_dict()`, `node.raw`, and `node.value` return
independent data snapshots; mutating their dictionaries or lists does not modify the
loaded configuration.

History records definitions of the same data path from lowest to highest priority.
When a list or value type is replaced, its old child paths are discarded. Resolving an
interpolation does not change the history of the node containing the expression.

## Current Limitations

- interpolation path parser supports unquoted dot keys and numeric list indices
- no nested interpolation expressions
- `to_toml()` is not implemented yet

## TODO

- [ ] review the details of interpolation

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
