from __future__ import annotations

from .tree import _DataNode
from .types import (
    DataPath,
    InterpolationDependency,
    ResolutionTrace,
    TraceNode,
)


def _build_resolution_trace(
    root: _DataNode,
    root_path: DataPath,
    direct_dependencies: dict[DataPath, tuple[InterpolationDependency, ...]],
) -> ResolutionTrace:
    nodes: list[TraceNode] = []
    dependencies: list[InterpolationDependency] = []
    visited_paths: set[DataPath] = set()

    def subtree_has_dependencies(path: DataPath, node: _DataNode) -> bool:
        if path in direct_dependencies:
            return True
        if isinstance(node.value, dict):
            return any(
                subtree_has_dependencies((*path, key), child)
                for key, child in node.value.items()
            )
        if isinstance(node.value, list):
            return any(
                subtree_has_dependencies((*path, index), child)
                for index, child in enumerate(node.value)
            )
        return False

    def visit(path: DataPath, include_descendants: bool) -> None:
        if path in visited_paths:
            return
        visited_paths.add(path)
        node = root._get_subnode(path)
        nodes.append(TraceNode(path=path, history=node.history))
        dependencies_at_path = direct_dependencies.get(path, ())
        dependencies.extend(dependencies_at_path)
        for dependency in dependencies_at_path:
            visit(dependency.source_path, include_descendants=True)
        if include_descendants and isinstance(node.value, dict):
            for key, child in node.value.items():
                child_path = (*path, key)
                if subtree_has_dependencies(child_path, child):
                    visit(child_path, include_descendants=True)
        elif include_descendants and isinstance(node.value, list):
            for index, child in enumerate(node.value):
                child_path = (*path, index)
                if subtree_has_dependencies(child_path, child):
                    visit(child_path, include_descendants=True)

    visit(root_path, include_descendants=True)
    return ResolutionTrace(
        root_path=root_path,
        nodes=tuple(nodes),
        dependencies=tuple(dependencies),
    )
