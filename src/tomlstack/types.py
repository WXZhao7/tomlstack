from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Literal, TypeAlias

DataPath = tuple[str | int, ...]

CONFIG_TABLE = "tomlstack"
ROOT_PATH: DataPath = ()


@dataclass(frozen=True, slots=True)
class TomlFile:
    str_: str  # original path
    path: Path  # resolved absolute path


@dataclass(frozen=True, slots=True)
class IncludeNode:
    file: TomlFile
    children: tuple[IncludeNode, ...]

    def render(self, absolute: bool = False) -> str:
        def format_file(file: TomlFile) -> str:
            if absolute:
                return f"{file.str_} -> {file.path}"
            return file.str_

        lines = [format_file(self.file)]

        def render_children(node: IncludeNode, prefix: str) -> None:
            for index, child in enumerate(node.children):
                is_last = index == len(node.children) - 1
                branch = "└── " if is_last else "├── "
                lines.append(prefix + branch + format_file(child.file))
                child_prefix = prefix + ("    " if is_last else "│   ")
                render_children(child, child_prefix)

        render_children(self, "")
        return "\n".join(lines)


InterpolationKind: TypeAlias = Literal["replace", "format", "embed"]


@dataclass(frozen=True, slots=True)
class InterpolationDependency:
    target_path: DataPath
    source_path: DataPath
    expression: str
    kind: InterpolationKind
    format_spec: str | None
    source_history: tuple[TomlFile, ...]


@dataclass(frozen=True, slots=True)
class TraceNode:
    path: DataPath
    history: tuple[TomlFile, ...]


@dataclass(frozen=True, slots=True)
class ResolutionTrace:
    root_path: DataPath
    nodes: tuple[TraceNode, ...]
    dependencies: tuple[InterpolationDependency, ...]


@dataclass(frozen=True, slots=True)
class _DataNode:
    value: _DataNodeValue
    history: tuple[TomlFile, ...]
    _materialized_cache: Any = field(
        init=False, default=None, repr=False, compare=False, hash=False
    )

    @property
    def materialized(self) -> Any:
        if self._materialized_cache is None:
            cached = self._to_plain_value(self)
            object.__setattr__(self, "_materialized_cache", cached)
        return self._materialized_cache

    @classmethod
    def _to_plain_value(cls, node: _DataNode) -> Any:
        if isinstance(node.value, dict):
            return {
                key: cls._to_plain_value(child) for key, child in node.value.items()
            }
        if isinstance(node.value, list):
            return [cls._to_plain_value(child) for child in node.value]
        return node.value

    def _get_subnode(self, path: DataPath) -> _DataNode:
        node = self
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


TomlScalar: TypeAlias = str | int | float | bool | date | time | datetime
_DataNodeValue: TypeAlias = TomlScalar | dict[str, _DataNode] | list[_DataNode]
