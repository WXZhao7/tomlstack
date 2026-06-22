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
from .types import ROOT_PATH, DataPath, _DataNode

EXPR_RE = re.compile(r"\$\{([^{}]+)\}")
ALLOWED_EMBED_TYPES = (str, int, float, bool, date, time, datetime)
ALLOWED_EMBED_TYPES_STR = ", ".join(t.__name__ for t in ALLOWED_EMBED_TYPES)


def _get_node(root: _DataNode, path: DataPath) -> _DataNode:
    node = root
    for part in path:
        if isinstance(part, str):
            if not isinstance(node.value, dict) or part not in node.value:
                raise KeyError(part)
            node = node.value[part]
        elif isinstance(part, int):
            if not isinstance(node.value, list) or part < 0 or part >= len(node.value):
                raise IndexError(part)
            node = node.value[part]
        else:
            raise TypeError(f"Invalid path part: {part!r}")
    return node


@dataclass
class _InterpolationState:
    raw_root: _DataNode
    resolved_cache: dict[DataPath, Any]
    resolving_stack: list[DataPath]


def resolve_interpolations(raw_root: _DataNode) -> dict[str, Any]:
    state = _InterpolationState(
        raw_root=raw_root, resolved_cache={}, resolving_stack=[]
    )
    resolved = _resolve_node(raw_root, ROOT_PATH, state)
    assert isinstance(resolved, dict)
    return resolved


def _resolve_node(node: _DataNode, path: DataPath, state: _InterpolationState) -> Any:
    """Recursively resolve interpolations in a value"""
    if isinstance(node.value, dict):
        return {
            key: _resolve_node(child, (*path, key), state)
            for key, child in node.value.items()
        }
    if isinstance(node.value, list):
        return [
            _resolve_node(child, (*path, index), state)
            for index, child in enumerate(node.value)
        ]
    if isinstance(node.value, str):
        try:
            return _resolve_string(node.value, state)
        except Exception as e:
            raise InterpolationError(f"Failed to resolve {node.value!r}") from e
    return node.value


def _resolve_string(str_expr: str, state: _InterpolationState) -> Any:
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
        resolved_value = _resolve_path_expr(path_expr, state)
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
        resolved_value = _resolve_path_expr(path_expr, state)
        parts.append(_format_value(resolved_value, fmt_spec))

        last = end
    parts.append(str_expr[last:])  # add the remaining literal part

    return "".join(parts)


def _resolve_path_expr(path_expr: str, state: _InterpolationState) -> Any:
    path = parse_path_expr(path_expr)

    if path in state.resolved_cache:
        return deepcopy(state.resolved_cache[path])

    if path in state.resolving_stack:
        chain = " -> ".join(format_path_expr(p) for p in [*state.resolving_stack, path])
        raise InterpolationCycleError(f"Interpolation cycle detected: {chain}")

    state.resolving_stack.append(path)

    try:
        raw_node = _get_node(state.raw_root, path)
        resolved = _resolve_node(raw_node, path, state)
        state.resolved_cache[path] = resolved
        return deepcopy(resolved)
    finally:
        state.resolving_stack.pop()


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
