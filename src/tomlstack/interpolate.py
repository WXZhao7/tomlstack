from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from .errors import (
    InterpolationCycleError,
    InterpolationError,
)
from .path_expr import format_path_expr, get_by_path, parse_path_expr
from .types import ROOT_PATH, DataPath

EXPR_RE = re.compile(r"\$\{([^{}]+)\}")
ALLOWED_EMBED_TYPES = (str, int, float, bool, date, time, datetime)
ALLOWED_EMBED_TYPES_STR = ", ".join(t.__name__ for t in ALLOWED_EMBED_TYPES)


@dataclass
class _InterpolationState:
    raw_data: dict[str, Any]
    resolved_cache: dict[DataPath, Any]
    resolving_stack: list[DataPath]


def resolve_interpolations(raw_data: dict[str, Any]) -> dict[str, Any]:
    state = _InterpolationState(
        raw_data=raw_data, resolved_cache={}, resolving_stack=[]
    )
    return _resolve_node(raw_data, ROOT_PATH, state)


def _resolve_node(node: Any, path: DataPath, state: _InterpolationState) -> Any:
    """Recursively resolve interpolations in a value"""
    if isinstance(node, dict):
        return {k: _resolve_node(v, (*path, k), state) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_node(v, (*path, i), state) for i, v in enumerate(node)]
    if isinstance(node, str):
        try:
            return _resolve_string(node, state)
        except Exception as e:
            raise InterpolationError(f"Failed to resolve {node!r}") from e
    return node


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
        return state.resolved_cache[path]

    if path in state.resolving_stack:
        chain = " -> ".join(format_path_expr(p) for p in [*state.resolving_stack, path])
        raise InterpolationCycleError(f"Interpolation cycle detected: {chain}")

    state.resolving_stack.append(path)

    try:
        raw_value = get_by_path(state.raw_data, path)
        resolved = _resolve_node(raw_value, path, state)
        state.resolved_cache[path] = resolved
        return resolved
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
