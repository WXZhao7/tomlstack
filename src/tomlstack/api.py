from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from os import PathLike
from typing import Any

from .interpolate import _ResolutionResult, resolve_interpolations
from .loader import load_toml_with_includes
from .nodes import Node
from .path_expr import get_by_path
from .trace import build_resolution_trace
from .tree import _DataNode
from .types import (
    DataPath,
    IncludeNode,
    InterpolationDependency,
    ResolutionTrace,
    TomlFile,
)


@dataclass
class TomlStack:
    _root: _DataNode
    _include_tree: IncludeNode
    _resolution: _ResolutionResult | None = field(
        init=False, default=None, repr=False, compare=False, hash=False
    )

    @property
    def raw(self) -> Any:
        return deepcopy(self._root.materialized)

    @property
    def resolved(self) -> dict[str, Any]:
        return self.to_dict()

    def resolve(self) -> TomlStack:
        if self._resolution is None:
            self._resolution = resolve_interpolations(self._root)
        return self

    def to_dict(self) -> dict[str, Any]:
        self.resolve()
        assert self._resolution is not None
        return deepcopy(self._resolution.data)

    def to_toml(self) -> str:
        raise NotImplementedError("to_toml is reserved for future implementation")

    def __getitem__(self, key: str) -> Node:
        if not isinstance(self._root.value, dict) or key not in self._root.value:
            raise KeyError(key)
        return Node(self, (key,))

    def _get_raw(self, path: DataPath) -> Any:
        return deepcopy(self._root._get_subnode(path).materialized)

    def _get_history(self, path: DataPath) -> tuple[TomlFile, ...]:
        return self._root._get_subnode(path).history

    def _get_value(self, path: DataPath) -> Any:
        self.resolve()
        assert self._resolution is not None
        return deepcopy(get_by_path(self._resolution.data, path))

    def _get_dependencies(self, path: DataPath) -> tuple[InterpolationDependency, ...]:
        self.resolve()
        assert self._resolution is not None
        return self._resolution.direct_dependencies.get(path, ())

    def _get_trace(self, path: DataPath) -> ResolutionTrace:
        self.resolve()
        assert self._resolution is not None
        return build_resolution_trace(
            self._root,
            path,
            self._resolution.direct_dependencies,
        )

    @property
    def include_tree(self) -> IncludeNode:
        return self._include_tree


def load(path: str | PathLike[str]) -> TomlStack:
    loaded = load_toml_with_includes(path)
    return TomlStack(_root=loaded.root, _include_tree=loaded.include_tree)
