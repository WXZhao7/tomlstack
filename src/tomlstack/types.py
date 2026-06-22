from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, TypeAlias

DataPath = tuple[str | int, ...]

CONFIG_TABLE = "tomlstack"
ROOT_PATH: DataPath = ()


@dataclass(frozen=True, slots=True)
class TomlFile:
    str_: str  # original path
    path: Path  # resolved absolute path


@dataclass(frozen=True, slots=True)
class TomlHist:
    file: TomlFile
    depth: int


@dataclass(frozen=True, slots=True)
class _DataNode:
    value: _DataNodeValue
    history: tuple[TomlHist, ...]
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


TomlScalar: TypeAlias = str | int | float | bool | date | time | datetime
_DataNodeValue: TypeAlias = TomlScalar | dict[str, _DataNode] | list[_DataNode]
