from __future__ import annotations

import tomllib
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, time
from os import PathLike
from pathlib import Path
from typing import Any, TypeAlias

from .errors import ContentError, IncludeCycleError
from .include import IncludeSpec
from .types import (
    CONFIG_TABLE,
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


TomlScalar: TypeAlias = str | int | float | bool | date | time | datetime
_DataNodeValue: TypeAlias = (
    TomlScalar | dict[str, "_DataNode"] | list["_DataNode"]
)


@dataclass(frozen=True, slots=True)
class _DataNode:
    value: _DataNodeValue
    history: tuple[TomlHist, ...]


@dataclass(frozen=True, slots=True)
class LoadResult:
    root: _DataNode


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
        current = _annotate(
            toml.data, TomlHist(file=entry, depth=ctx.depth)
        )
        if not toml.includes:
            return LoadResult(root=current)
        # Includes are merged in order; later includes override earlier ones.
        # The current file has the highest precedence.
        include_spec = IncludeSpec.from_toml(entry, toml.anchors)
        merged = _DataNode(value={}, history=())
        for raw_path in toml.includes:
            abs_path = include_spec.resolve_include_path(raw_path)
            included = _load_file(TomlFile(str_=raw_path, path=abs_path), ctx)
            merged = _merge_nodes(merged, included.root)
        return LoadResult(root=_merge_nodes(merged, current))


def _annotate(value: Any, hist: TomlHist) -> _DataNode:
    annotated: _DataNodeValue
    if isinstance(value, dict):
        annotated = {key: _annotate(child, hist) for key, child in value.items()}
    elif isinstance(value, list):
        annotated = [_annotate(child, hist) for child in value]
    else:
        annotated = value
    return _DataNode(value=annotated, history=(hist,))


def _merge_nodes(low: _DataNode, high: _DataNode) -> _DataNode:
    """Merge two nodes with high priority overriding low priority."""
    history = low.history + high.history
    if isinstance(low.value, dict) and isinstance(high.value, dict):
        merged = dict(low.value)
        for key, high_child in high.value.items():
            if key in merged:
                merged[key] = _merge_nodes(merged[key], high_child)
            else:
                merged[key] = high_child
        return _DataNode(value=merged, history=history)
    return _DataNode(value=high.value, history=history)


def _get_node(root: _DataNode, path: DataPath) -> _DataNode:
    node = root
    for part in path:
        if isinstance(part, str):
            if not isinstance(node.value, dict) or part not in node.value:
                raise KeyError(part)
            node = node.value[part]
        elif isinstance(part, int):
            if (
                not isinstance(node.value, list)
                or part < 0
                or part >= len(node.value)
            ):
                raise IndexError(part)
            node = node.value[part]
        else:
            raise TypeError(f"Invalid path part: {part!r}")
    return node


def _materialize(node: _DataNode) -> Any:
    if isinstance(node.value, dict):
        return {key: _materialize(child) for key, child in node.value.items()}
    if isinstance(node.value, list):
        return [_materialize(child) for child in node.value]
    return node.value


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
