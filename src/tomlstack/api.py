from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from typing import Any

from .interpolate import resolve_interpolations
from .loader import LoadResult, load_toml_with_includes
from .nodes import Node
from .path_expr import get_by_path
from .types import PathKey, TomlHist


@dataclass
class TomlStack:
    _merged_data: dict[str, Any]
    _resolved_data: dict[str, Any] | None
    _history: dict[PathKey, list[TomlHist]]

    @property
    def view(self) -> dict[str, Any]:
        if self._resolved_data is None:
            return self._merged_data
        else:
            return self._resolved_data

    def resolve(self) -> TomlStack:
        if self._resolved_data is None:
            self._resolved_data = resolve_interpolations(self._merged_data)
        return self

    def to_dict(self, resolve: bool = True) -> dict[str, Any]:
        if resolve:
            if self._resolved_data is None:
                self.resolve()
            assert self._resolved_data is not None
            return self._resolved_data
        return self._merged_data

    def to_toml(self) -> str:
        raise NotImplementedError("to_toml is reserved for future implementation")

    def __getitem__(self, key: str) -> Node:
        if key not in self._merged_data:
            raise KeyError(key)
        return Node(self, (key,))

    def _get_raw(self, path: PathKey) -> Any:
        return get_by_path(self._merged_data, path)

    def _get_value(self, path: PathKey) -> Any:
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
        _merged_data=result.data, _resolved_data=None, _history=result.history
    )
