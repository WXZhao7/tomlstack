from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .types import DataPath, InterpolationDependency, ResolutionTrace, TomlFile


@dataclass(frozen=True, slots=True, init=False)
class TomlNode:
    """A query result returned by :class:`TomlStack` navigation."""

    _source: _NodeSource
    path: DataPath

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("TomlNode instances are created by TomlStack navigation")

    @classmethod
    def _from_path(cls, source: _NodeSource, path: DataPath) -> TomlNode:
        try:
            source._get_raw(path)
        except (KeyError, IndexError):
            raise KeyError(f"Node path does not exist: {path}") from None
        node = object.__new__(cls)
        object.__setattr__(node, "_source", source)
        object.__setattr__(node, "path", path)
        return node

    @property
    def raw(self) -> Any:
        return self._source._get_raw(self.path)

    @property
    def value(self) -> Any:
        return self._source._get_value(self.path)

    @property
    def origin(self) -> TomlFile:
        return self.history[-1]

    @property
    def history(self) -> tuple[TomlFile, ...]:
        return self._source._get_history(self.path)

    @property
    def dependencies(self) -> tuple[InterpolationDependency, ...]:
        return self._source._get_dependencies(self.path)

    def explain(self) -> ResolutionTrace:
        return self._source._get_trace(self.path)

    def preview(self) -> str:
        return _render_preview(self.raw)

    def __getitem__(self, key: str | int) -> TomlNode:
        value = self.raw
        if isinstance(key, int):
            if not isinstance(value, list):
                raise TypeError(f"Cannot index non-list node with int key: {self.path}")
            if key < 0 or key >= len(value):
                raise IndexError(key)
            return self._from_path(self._source, (*self.path, key))
        if isinstance(key, str):
            if not isinstance(value, dict):
                raise TypeError(f"Cannot index non-dict node with str key: {self.path}")
            if key not in value:
                raise KeyError(key)
            return self._from_path(self._source, (*self.path, key))
        raise TypeError(f"Unsupported key type: {type(key)!r}")

    def __repr__(self) -> str:
        return (
            f"TomlNode(path={self.path!r}, raw={self.raw!r}, "
            f"value={self.value!r}, origin={self.origin!r})"
        )


class _NodeSource(Protocol):
    def _get_raw(self, path: DataPath) -> Any: ...

    def _get_value(self, path: DataPath) -> Any: ...

    def _get_history(self, path: DataPath) -> tuple[TomlFile, ...]: ...

    def _get_dependencies(
        self, path: DataPath
    ) -> tuple[InterpolationDependency, ...]: ...

    def _get_trace(self, path: DataPath) -> ResolutionTrace: ...


def _render_preview(value: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        lines = ["{"]
        for key, child in value.items():
            child_rendered = _render_preview(child, indent + 1)
            lines.append(f"{pad}  {key}: {child_rendered}")
        lines.append(f"{pad}" + "}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = ["["]
        for child in value:
            child_rendered = _render_preview(child, indent + 1)
            lines.append(f"{pad}  {child_rendered}")
        lines.append(f"{pad}" + "]")
        return "\n".join(lines)
    return repr(value)
