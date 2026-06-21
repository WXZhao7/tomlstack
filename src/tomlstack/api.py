from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from typing import Any

from .interpolate import resolve_interpolations
from .loader import (
    LoadResult,
    _DataNode,
    _get_node,
    _materialize,
    load_toml_with_includes,
)
from .nodes import Node
from .path_expr import get_by_path
from .types import DataPath, TomlHist


@dataclass
class TomlStack:
    _root: _DataNode
    _resolved_data: dict[str, Any] | None

    @property
    def view(self) -> dict[str, Any]:
        if self._resolved_data is None:
            return _materialize(self._root)
        else:
            return self._resolved_data

    def resolve(self) -> TomlStack:
        if self._resolved_data is None:
            self._resolved_data = resolve_interpolations(self._root)
        return self

    def to_dict(self, resolve: bool = True) -> dict[str, Any]:
        if resolve:
            if self._resolved_data is None:
                self.resolve()
            assert self._resolved_data is not None
            return self._resolved_data
        return _materialize(self._root)

    def to_toml(self) -> str:
        raise NotImplementedError("to_toml is reserved for future implementation")

    def __getitem__(self, key: str) -> Node:
        if not isinstance(self._root.value, dict) or key not in self._root.value:
            raise KeyError(key)
        return Node(self, (key,))

    def _get_raw(self, path: DataPath) -> Any:
        return _materialize(_get_node(self._root, path))

    def _get_history(self, path: DataPath) -> tuple[TomlHist, ...]:
        return _get_node(self._root, path).history

    def _get_value(self, path: DataPath) -> Any:
        if self._resolved_data is None:
            self.resolve()
        assert self._resolved_data is not None
        return get_by_path(self._resolved_data, path)

    def include_tree(self, level: int = 0, absolute: bool = False): ...

    # history[()]可以记录整个文件的层级, 可以导出文件层级, 形如
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
    result: LoadResult = load_toml_with_includes(path)
    return TomlStack(
        _root=result.root,
        _resolved_data=None,
    )
