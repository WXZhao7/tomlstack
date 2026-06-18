from __future__ import annotations

import tomllib
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any

from .errors import ContentError, IncludeCycleError
from .include import IncludeSpec
from .types import (
    CONFIG_TABLE,
    ROOT_PATH,
    DataPath,
    TomlFile,
    TomlHist,
)


@dataclass(frozen=True, slots=True)
class ParsedToml:
    metadata: dict[str, Any]
    includes: list[str]
    anchors: dict[str, str]
    data: dict[str, Any]


@dataclass
class LoadResult:
    data: dict[str, Any]
    history: dict[DataPath, list[TomlHist]]


@dataclass
class _LoadContext:
    file_stack: list[TomlFile] = field(default_factory=list)
    # current include stack for cycle detection

    @property
    def depth(self) -> int:
        return len(self.file_stack)

    def _render_include_chain(self) -> str:
        return "\n".join(f"\t{f.str_} -> {f.path}" for f in self.file_stack)

    @contextmanager
    def enter_file(self, entry: TomlFile):
        self._validate_cycle_include(entry)
        toml = parse_raw_file(entry.path)

        self.file_stack.append(entry)
        try:
            yield toml
        finally:
            self.file_stack.pop()

    def _validate_cycle_include(self, entry: TomlFile) -> None:

        def render_cycle_include() -> str:
            msg = f"Include cycle detected when load {self.file_stack[0].str_!r}\n"
            for f in self.file_stack + [entry]:
                if f.path == entry.path:
                    msg += f"\t=> {f.str_} -> {f.path}\n"
                else:
                    msg += f"\t   {f.str_} -> {f.path}\n"
            return msg

        for file in self.file_stack:
            if file.path == entry.path:
                raise IncludeCycleError(render_cycle_include())


def load_toml_with_includes(root_file: str | PathLike[str]) -> LoadResult:
    abs_path = Path(root_file).expanduser().resolve()
    result = _load_file(TomlFile(str_=str(root_file), path=abs_path), _LoadContext())
    return result


def _load_file(entry: TomlFile, ctx: _LoadContext) -> LoadResult:

    with ctx.enter_file(entry) as toml:
        current_data = toml.data
        current_history = record_history(
            toml.data, TomlHist(file=entry, depth=ctx.depth)
        )
        if not toml.includes:
            return LoadResult(data=current_data, history=current_history)
        # Includes are merged in order; later includes override earlier ones.
        # The current file has the highest precedence.
        include_spec = IncludeSpec.from_toml(entry, toml.anchors)
        merged_data: dict[str, Any] = {}
        merged_history: dict[DataPath, list[TomlHist]] = {}
        for raw_path in toml.includes:
            abs_path = include_spec.resolve_include_path(raw_path)
            included = _load_file(TomlFile(str_=raw_path, path=abs_path), ctx)
            merged_data = merge_data(merged_data, included.data)
            merged_history = merge_history(merged_history, included.history)
        merged_data = merge_data(merged_data, current_data)
        merged_history = merge_history(merged_history, current_history)
        return LoadResult(data=merged_data, history=merged_history)


def record_history(data: Any, hist: TomlHist):
    history: dict[DataPath, list[TomlHist]] = {}

    def walk(value: Any, path: DataPath) -> None:
        history.setdefault(path, []).append(hist)
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, (*path, key))
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, (*path, idx))

    walk(data, ROOT_PATH)
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
    low: dict[DataPath, list[TomlHist]], high: dict[DataPath, list[TomlHist]]
) -> dict[DataPath, list[TomlHist]]:
    merged = {path: entries[:] for path, entries in low.items()}  # !!! important?
    for path, entries in high.items():
        merged.setdefault(path, []).extend(entries)
    return merged


def parse_raw_file(path: Path) -> ParsedToml:
    with path.open("rb") as f:
        data = tomllib.load(f)

    metadata = data.pop(CONFIG_TABLE, {})
    if not isinstance(metadata, dict):
        raise ContentError(f"Invalid {CONFIG_TABLE} table in {path}")

    includes: list[str] = []
    raw_include = data.pop("include", None)

    if raw_include is None:
        pass
    elif isinstance(raw_include, str):
        includes.append(raw_include)
    elif isinstance(raw_include, list):
        for item in raw_include:
            if not isinstance(item, str):
                raise ContentError(f"Invalid include item {item!r} in {path}")
        includes.extend(raw_include)
    else:
        raise ContentError(f"Invalid include specification in {path}")

    anchors: dict[str, str] = {}
    raw_anchors = metadata.get("anchors", None)
    if raw_anchors is None:
        pass
    elif isinstance(raw_anchors, dict):
        for label, value in raw_anchors.items():
            if not isinstance(value, str):
                raise ContentError(f"Invalid anchor {label!r} -> {value!r} in {path}")
            anchors[label] = value
    else:
        raise ContentError(f"Invalid anchors specification in {path}")

    return ParsedToml(metadata=metadata, includes=includes, anchors=anchors, data=data)
