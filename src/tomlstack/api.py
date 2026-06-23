from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from os import PathLike
from typing import Any

from .interpolate import _ResolutionResult, resolve_interpolations
from .loader import _DataNode, load_toml_with_includes
from .nodes import Node
from .path_expr import get_by_path
from .types import (
    DataPath,
    InterpolationDependency,
    ResolutionTrace,
    TomlHist,
    TraceNode,
)


@dataclass
class TomlStack:
    _root: _DataNode
    _resolution: _ResolutionResult | None = field(init=False, default=None)

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

    def _get_history(self, path: DataPath) -> tuple[TomlHist, ...]:
        return self._root._get_subnode(path).history

    def _get_value(self, path: DataPath) -> Any:
        self.resolve()
        assert self._resolution is not None
        return deepcopy(get_by_path(self._resolution.data, path))

    def _get_dependencies(
        self, path: DataPath
    ) -> tuple[InterpolationDependency, ...]:
        self.resolve()
        assert self._resolution is not None
        return self._resolution.direct_dependencies.get(path, ())

    def _get_trace(self, path: DataPath) -> ResolutionTrace:
        self.resolve()
        assert self._resolution is not None
        resolution = self._resolution
        nodes: list[TraceNode] = []
        dependencies: list[InterpolationDependency] = []
        visited_paths: set[DataPath] = set()

        def visit(node_path: DataPath, include_descendants: bool) -> None:
            if node_path in visited_paths:
                return
            visited_paths.add(node_path)
            node = self._root._get_subnode(node_path)
            nodes.append(TraceNode(path=node_path, history=node.history))
            direct = resolution.direct_dependencies.get(node_path, ())
            dependencies.extend(direct)
            for dependency in direct:
                visit(dependency.source_path, include_descendants=True)
            if include_descendants and isinstance(node.value, dict):
                for key, child in node.value.items():
                    child_path = (*node_path, key)
                    if self._subtree_has_dependencies(child_path, child):
                        visit(child_path, include_descendants=True)
            elif include_descendants and isinstance(node.value, list):
                for index, child in enumerate(node.value):
                    child_path = (*node_path, index)
                    if self._subtree_has_dependencies(child_path, child):
                        visit(child_path, include_descendants=True)

        visit(path, include_descendants=True)
        return ResolutionTrace(
            root_path=path, nodes=tuple(nodes), dependencies=tuple(dependencies)
        )

    def _subtree_has_dependencies(self, path: DataPath, node: _DataNode) -> bool:
        assert self._resolution is not None
        if path in self._resolution.direct_dependencies:
            return True
        if isinstance(node.value, dict):
            return any(
                self._subtree_has_dependencies((*path, key), child)
                for key, child in node.value.items()
            )
        if isinstance(node.value, list):
            return any(
                self._subtree_has_dependencies((*path, index), child)
                for index, child in enumerate(node.value)
            )
        return False

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
