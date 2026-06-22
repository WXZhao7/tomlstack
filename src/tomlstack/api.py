from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from os import PathLike
from typing import Any

from .interpolate import resolve_interpolations
from .loader import _DataNode, load_toml_with_includes
from .nodes import Node
from .path_expr import get_by_path
from .types import DataPath, TomlHist


@dataclass
class TomlStack:
    _root: _DataNode
    _resolved: dict[str, Any] | None = field(init=False, default=None)

    @property
    def raw(self) -> Any:
        return deepcopy(self._root.materialized)

    @property
    def resolved(self) -> dict[str, Any]:
        return self.to_dict()

    def resolve(self) -> TomlStack:
        if self._resolved is None:
            self._resolved = resolve_interpolations(self._root)
        return self

    def to_dict(self) -> dict[str, Any]:
        self.resolve()
        assert self._resolved is not None
        return deepcopy(self._resolved)

    def to_toml(self) -> str:
        raise NotImplementedError("to_toml is reserved for future implementation")

    def __getitem__(self, key: str) -> Node:
        if not isinstance(self._root.value, dict) or key not in self._root.value:
            raise KeyError(key)
        return Node(self, (key,))

    def _get_raw(self, path: DataPath) -> Any:
        return deepcopy(self._root._get_subnode(path).materialized)

    def _get_history(self, path: DataPath) -> tuple[TomlHist, ...]:
        return self._root._get_subnode(path).history

    def _get_value(self, path: DataPath) -> Any:
        if self._resolved is None:
            self.resolve()
        assert self._resolved is not None
        return deepcopy(get_by_path(self._resolved, path))

    def include_tree(self, level: int = 0, absolute: bool = False): ...

    #
    # main.toml
    # ├─ ./a.toml
    # │  └─ @root/base.toml
    # ├─ /abs/path/c.toml
    # │  └─ @root/base.toml
    # └─ ./b.toml
    #    └─ @root/base.toml
    #
    # main.toml -> /abs/project/main.toml
    # ├─ ./a.toml  -> /abs/path/a.toml
    # │  └─ @root/base.toml -> /abs/shared/base.toml
    # └─ ./b.toml  -> /abs/path/b.toml
    #    └─ @root/base.toml -> /abs/shared/base.toml


def load(path: str | PathLike[str]) -> TomlStack:
    return TomlStack(_root=load_toml_with_includes(path))
