from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .types import PathKey, TomlHist


@dataclass
class Node:
    _cfg: ConfigProtocol
    key: PathKey

    def __post_init__(self) -> None:
        if self.key not in self._cfg._history:
            raise KeyError(f"Node path does not exist: {self.key}")

    @property
    def raw(self) -> Any:
        return self._cfg._get_raw(self.key)

    @property
    def value(self) -> Any:
        return self._cfg._get_value(self.key)

    @property
    def resolved(self) -> Any:
        return self.value

    @property
    def origin(self) -> TomlHist:
        return self._cfg._history[self.key][-1]

    @property
    def history(self) -> tuple[TomlHist, ...]:
        return tuple(self._cfg._history[self.key])

    def preview(self) -> str:
        return _render_preview(self.raw)

    def __getitem__(self, key: str | int) -> Node:
        value = self.raw
        if isinstance(key, int):
            if not isinstance(value, list):
                raise TypeError(f"Cannot index non-list node with int key: {self.key}")
            if key < 0 or key >= len(value):
                raise IndexError(key)
            return Node(self._cfg, (*self.key, key))
        if isinstance(key, str):
            if not isinstance(value, dict):
                raise TypeError(f"Cannot index non-dict node with str key: {self.key}")
            if key not in value:
                raise KeyError(key)
            return Node(self._cfg, (*self.key, key))
        raise TypeError(f"Unsupported key type: {type(key)!r}")

    def __repr__(self) -> str:
        return (
            f"Node(path={self.key!r}, raw={self.raw!r}, "
            f"value={self.value!r}, origin={self.origin!r})"
        )


class ConfigProtocol(Protocol):
    _history: dict[PathKey, list[TomlHist]]

    def _get_raw(self, path: PathKey) -> Any: ...

    def _get_value(self, path: PathKey) -> Any: ...


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
