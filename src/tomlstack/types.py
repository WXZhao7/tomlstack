from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Literal, TypeAlias

DataPath = tuple[str | int, ...]

CONFIG_TABLE = "tomlstack"
ROOT_PATH: DataPath = ()


@dataclass(frozen=True, slots=True)
class TomlFile:
    reference: str  # root input or raw include expression
    path: Path  # resolved absolute path


@dataclass(frozen=True, slots=True)
class IncludeNode:
    file: TomlFile
    children: tuple[IncludeNode, ...]

    def render(self, absolute: bool = False) -> str:
        def format_file(file: TomlFile) -> str:
            if absolute:
                return f"{file.reference} -> {file.path}"
            return file.reference

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


TomlScalar: TypeAlias = str | int | float | bool | date | time | datetime
