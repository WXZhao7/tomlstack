from __future__ import annotations

import tomllib
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .base import (
    SUPPORTED_VERSIONS,
    UNDECLARED_VERSION,
    PathHist,
    PathKey,
    PathRec,
    RawToml,
)
from .errors import ContentError, IncludeCycleError, VersionError
from .include import IncludeSpec

INTERNAL_FIELDS = {"include", "__meta__"}
ROOT_HISTORY_KEY: PathKey = ()


@dataclass
class LoadResult:
    data: dict[str, Any]
    history: dict[PathKey, list[PathHist]]


@dataclass
class _LoadContext:
    file_stack: list[PathRec] = field(default_factory=list)
    # current include stack for cycle detection
    file_versions: dict[Path, int] = field(default_factory=dict)
    # mapping of file paths to their declared or inferred version

    @property
    def depth(self) -> int:
        return len(self.file_stack)

    def _render_include_chain(self) -> str:
        return "\n".join(f"\t{f.raw} -> {f.path}" for f in self.file_stack)

    @contextmanager
    def enter_file(self, entry: PathRec):
        toml = parse_raw_file(entry.path)

        self._validate_cycle_include(entry)
        try:
            version = self._get_version(toml.meta)
            self._validate_version(version)
        except VersionError as e:
            raise VersionError(
                f"Version conflict when including {entry.raw!r} "
                f"resolved as {entry.path}\n"
                "Current include chain:\n" + self._render_include_chain()
            ) from e

        self.file_stack.append(entry)
        self.file_versions[entry.path] = version
        try:
            yield toml
        finally:
            self.file_stack.pop()

    @classmethod
    def _get_version(cls, meta: dict[str, Any]) -> int:
        v = meta.get("version")
        if v is None:
            return UNDECLARED_VERSION
        if not isinstance(v, int):
            raise VersionError(f"Invalid type __meta__.version {v!r}")
        if v not in SUPPORTED_VERSIONS:
            raise VersionError(f"Unsupported __meta__.version {v!r}")
        return v

    def _validate_version(self, version: int) -> None:
        if version == UNDECLARED_VERSION:
            return
        declared_version = set(self.file_versions.values())
        declared_version.discard(UNDECLARED_VERSION)
        declared_version.add(version)

        if len(declared_version) > 1:
            raise VersionError(
                f"Conflicting __meta__.version value {version} "
                f"with declared {declared_version!r}"
            )

    def _validate_cycle_include(self, entry: PathRec) -> None:

        def render_cycle_include() -> str:
            root = self.file_stack[0]
            msg = f"Include cycle detected when load {root.raw!r}\n"
            for f in self.file_stack + [entry]:
                if f.path == entry.path:
                    msg += f"\t=> {f.raw} -> {f.path}\n"
                else:
                    msg += f"\t   {f.raw} -> {f.path}\n"
            return msg

        for file in self.file_stack:
            if file.path == entry.path:
                raise IncludeCycleError(render_cycle_include())


def load_toml_with_includes(root_file: Path) -> LoadResult:
    abs_path = root_file.expanduser().resolve()
    result = _load_file(PathRec(raw=str(root_file), path=abs_path), _LoadContext())
    return result


def _load_file(entry: PathRec, ctx: _LoadContext) -> LoadResult:

    with ctx.enter_file(entry) as toml:
        current_data = toml.body
        current_history = record_history(
            toml.body, PathHist(raw=entry.raw, path=entry.path, depth=ctx.depth)
        )
        include_spec = IncludeSpec.from_toml(toml)
        if toml.includes:
            merged_data: dict[str, Any] = {}
            merged_history: dict[PathKey, list[PathHist]] = {}
            for raw_path in toml.includes:
                abs_path = include_spec.resolve_include_path(raw_path)
                included = _load_file(PathRec(raw=raw_path, path=abs_path), ctx)
                merged_data = merge_data(merged_data, included.data)
                merged_history = merge_history(merged_history, included.history)
            merged_data = merge_data(merged_data, current_data)
            merged_history = merge_history(merged_history, current_history)
            return LoadResult(data=merged_data, history=merged_history)
        else:
            return LoadResult(data=current_data, history=current_history)


def record_history(data: Any, hist: PathHist):
    history: dict[PathKey, list[PathHist]] = {}

    def walk(value: Any, path: PathKey) -> None:
        history.setdefault(path, []).append(hist)
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, (*path, key))
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, (*path, idx))

    walk(data, ROOT_HISTORY_KEY)
    return history


def merge_data(low: dict[str, Any], high: dict[str, Any]) -> dict[str, Any]:
    """Merge two dictionaries with high priority overriding low priority."""
    result: dict[str, Any] = deepcopy(low)
    for key, high_value in high.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(high_value, dict)
        ):
            result[key] = merge_data(result[key], high_value)
        else:
            result[key] = deepcopy(high_value)
    return result


def merge_history(
    low: dict[PathKey, list[PathHist]], high: dict[PathKey, list[PathHist]]
) -> dict[PathKey, list[PathHist]]:
    merged = {path: entries[:] for path, entries in low.items()}  # !!! important?
    for path, entries in high.items():
        merged.setdefault(path, []).extend(entries)
    return merged


def parse_raw_file(path: Path) -> RawToml:
    with path.open("rb") as f:
        data = tomllib.load(f)

    if not isinstance(data, dict):
        raise ContentError(f"Top-level TOML object must be a table: {path}")

    meta = data.pop("__meta__", {})
    if not isinstance(meta, dict):
        raise ContentError(f"Invalid __meta__ table in {path}")

    includes: list[str] = []
    raw_include = data.pop("include", None)

    if raw_include is None:
        pass
    elif isinstance(raw_include, str):
        includes.append(raw_include)
    elif isinstance(raw_include, list) and all(
        isinstance(item, str) for item in raw_include
    ):
        includes.extend(raw_include)
    else:
        raise ContentError(f"Invalid include specification in {path}")

    return RawToml(path=path, meta=meta, body=data, includes=includes)
