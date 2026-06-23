from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from .errors import (
    InterpolationCycleError,
    InterpolationError,
)
from .path_expr import format_path_expr, parse_path_expr
from .types import (
    ROOT_PATH,
    DataPath,
    InterpolationDependency,
    InterpolationKind,
    TomlFile,
    _DataNode,
)

EXPR_RE = re.compile(r"\$\{([^{}]+)\}")
ALLOWED_EMBED_TYPES = (str, int, float, bool, date, time, datetime)
ALLOWED_EMBED_TYPES_STR = ", ".join(t.__name__ for t in ALLOWED_EMBED_TYPES)


@dataclass
class _InterpolationState:
    raw_root: _DataNode
    resolved_cache: dict[DataPath, Any]
    resolving_stack: list[DataPath]
    direct_dependencies: dict[DataPath, list[InterpolationDependency]]


@dataclass(frozen=True, slots=True)
class _ResolutionResult:
    data: dict[str, Any]
    direct_dependencies: dict[DataPath, tuple[InterpolationDependency, ...]]


def resolve_interpolations(raw_root: _DataNode) -> _ResolutionResult:
    state = _InterpolationState(
        raw_root=raw_root,
        resolved_cache={},
        resolving_stack=[],
        direct_dependencies={},
    )
    resolved = _resolve_node(raw_root, ROOT_PATH, state)
    assert isinstance(resolved, dict)
    return _ResolutionResult(
        data=resolved,
        direct_dependencies={
            path: tuple(dependencies)
            for path, dependencies in state.direct_dependencies.items()
        },
    )


def _resolve_node(node: _DataNode, path: DataPath, state: _InterpolationState) -> Any:
    """Recursively resolve interpolations in a value"""
    if path in state.resolved_cache:
        return deepcopy(state.resolved_cache[path])

    if path in state.resolving_stack:
        chain = " -> ".join(format_path_expr(p) for p in [*state.resolving_stack, path])
        raise InterpolationCycleError(f"Interpolation cycle detected: {chain}")

    state.resolving_stack.append(path)
    try:
        resolved: Any
        if isinstance(node.value, dict):
            resolved = {
                key: _resolve_node(child, (*path, key), state)
                for key, child in node.value.items()
            }
        elif isinstance(node.value, list):
            resolved = [
                _resolve_node(child, (*path, index), state)
                for index, child in enumerate(node.value)
            ]
        elif isinstance(node.value, str):
            try:
                resolved = _resolve_string(node.value, path, state)
            except Exception as e:
                raise InterpolationError(f"Failed to resolve {node.value!r}") from e
        else:
            resolved = node.value
        state.resolved_cache[path] = resolved
        return deepcopy(resolved)
    finally:
        state.resolving_stack.pop()


def _resolve_string(
    str_expr: str, target_path: DataPath, state: _InterpolationState
) -> Any:
    """
    Resolve interpolations in a string value.

    Example:
        "foo" -> "foo" (no interpolation)
        "${bar}" -> data["bar"] (keep original type)
        "Hello, ${user.name}!" -> "Hello, Alice!" (embedded interpolation)

    :param str_expr: The string expression to resolve
    :type str_expr: str
    :param state: The interpolation state
    :type state: _InterpolationState
    :return: The resolved value
    :rtype: Any
    """
    matches = list(EXPR_RE.finditer(str_expr))

    if not matches:
        # no interpolation, return the original value
        return str_expr

    # simple case: the whole string is a single interpolation
    # return the raw value with original type
    # e.g. foo = "${bar}"
    # if format spec is present, still return the formatted string
    # e.g. date_str = "${date_value:%Y-%m-%d}"
    if len(matches) == 1 and matches[0].span() == (0, len(str_expr)):
        interpolation = matches[0].group(1)
        path_expr, fmt_sep, fmt_spec = interpolation.partition(":")
        kind: InterpolationKind = "format" if fmt_sep else "replace"
        resolved_value = _resolve_path_expr(
            path_expr,
            target_path,
            matches[0].group(0),
            kind,
            fmt_spec if fmt_sep else None,
            state,
        )
        if fmt_sep:
            return _format_value(resolved_value, fmt_spec)
        return resolved_value

    # complex case: the string contains one or more interpolations
    # return a string with all interpolations resolved and formatted
    # e.g. greeting = "Hello, ${user.name}!"
    parts: list[str] = []
    last = 0
    for match in matches:
        start, end = match.span()
        # add the literal part before the interpolation
        parts.append(str_expr[last:start])

        interpolation = match.group(1)
        path_expr, _, fmt_spec = interpolation.partition(":")
        resolved_value = _resolve_path_expr(
            path_expr,
            target_path,
            match.group(0),
            "embed",
            fmt_spec or None,
            state,
        )
        parts.append(_format_value(resolved_value, fmt_spec))

        last = end
    parts.append(str_expr[last:])  # add the remaining literal part

    return "".join(parts)


def _resolve_path_expr(
    path_expr: str,
    target_path: DataPath,
    expression: str,
    kind: InterpolationKind,
    format_spec: str | None,
    state: _InterpolationState,
) -> Any:
    path = parse_path_expr(path_expr)
    raw_node = state.raw_root._get_subnode(path)
    _record_dependency(
        target_path,
        path,
        expression,
        kind,
        format_spec,
        raw_node.history,
        state,
    )
    return _resolve_node(raw_node, path, state)


def _record_dependency(
    target_path: DataPath,
    source_path: DataPath,
    expression: str,
    kind: InterpolationKind,
    format_spec: str | None,
    source_history: tuple[TomlFile, ...],
    state: _InterpolationState,
) -> None:
    state.direct_dependencies.setdefault(target_path, []).append(
        InterpolationDependency(
            target_path=target_path,
            source_path=source_path,
            expression=expression,
            kind=kind,
            format_spec=format_spec,
            source_history=source_history,
        )
    )


def _format_value(value: Any, fmt_spec: str) -> str:
    """Format a value using the given format specification"""
    if not isinstance(value, ALLOWED_EMBED_TYPES):
        raise InterpolationError(
            f"Cannot format value of type {type(value).__name__} "
            f"with  format spec '{fmt_spec}', "
            f"only supports {ALLOWED_EMBED_TYPES_STR}"
        )
    if isinstance(value, (date, time, datetime)):
        return value.strftime(fmt_spec)
    return format(value, fmt_spec)
