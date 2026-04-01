from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from .base import ROOT_PATH, PathKey
from .errors import (
    InterpolationCycleError,
    InterpolationError,
    InterpolationUndefinedError,
)
from .path_expr import format_path_expr, get_by_path, parse_path_expr

EXPR_RE = re.compile(r"\$\{([^{}]+)\}")
ALLOWED_EMBED_TYPES = (str, int, float, date, time, datetime)
ALLOWED_EMBED_TYPES_STR = ", ".join(t.__name__ for t in ALLOWED_EMBED_TYPES)


@dataclass
class _State:
    raw: dict[str, Any]
    cache: dict[PathKey, Any]
    stack: list[PathKey]


def resolve_interpolations(raw_data: dict[str, Any]) -> dict[str, Any]:
    state = _State(raw=raw_data, cache={}, stack=[])
    return _resolve_value(raw_data, ROOT_PATH, state)


def _resolve_value(value: Any, path: PathKey, state: _State) -> Any:
    """Recursively resolve interpolations in a value"""
    if isinstance(value, dict):
        return {k: _resolve_value(v, (*path, k), state) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(v, (*path, i), state) for i, v in enumerate(value)]
    if isinstance(value, str):
        return _resolve_string(value, path, state)
    return value


def _resolve_string(value: str, path: PathKey, state: _State) -> Any:
    """
    Resolve interpolations in a string value.

    :param value: The string value to resolve
    :type value: str
    :param path: The path to the current value
    :type path: PathKey
    :param state: The interpolation state
    :type state: _State
    :return: The resolved value
    :rtype: Any
    """
    matches = list(EXPR_RE.finditer(value))

    if not matches:
        # no interpolation, return the original value
        return value

    # simple case: the whole string is a single interpolation
    # return the raw value with original type
    # e.g. foo = "${bar}"
    # if format spec is present, still return the formatted string
    # e.g. date_str = "${date_value:%Y-%m-%d}"
    if len(matches) == 1 and matches[0].span() == (0, len(value)):
        expr = matches[0].group(1)
        ref, fmt_spec = _split_expr(expr)
        try:
            ref_path = parse_path_expr(ref)
        except ValueError as exc:
            raise InterpolationError(
                f"Invalid interpolation expression '{expr}' "
                f"at {format_path_expr(path)}: {exc}"
            ) from exc
        ref_value = _resolve_reference(ref_path, expr, path, state)
        if fmt_spec is None:
            return ref_value
        return _format_value(ref_value, fmt_spec)

    # complex case: the string contains one or more interpolations
    # return a string with all interpolations resolved and formatted
    # e.g. greeting = "Hello, ${user.name}!"
    parts: list[str] = []
    last = 0
    for match in matches:
        start, end = match.span()
        # add the literal part before the interpolation
        parts.append(value[last:start])

        expr = match.group(1)
        ref, fmt_spec = _split_expr(expr)
        try:
            ref_path = parse_path_expr(ref)
        except ValueError as exc:
            raise InterpolationError(
                f"Invalid interpolation expression '{expr}' "
                f"at {format_path_expr(path)}: {exc}"
            ) from exc
        ref_value = _resolve_reference(ref_path, expr, path, state)
        if not isinstance(ref_value, ALLOWED_EMBED_TYPES):
            raise InterpolationError(
                f"Embedded interpolation in {format_path_expr(path)} "
                f"only supports {ALLOWED_EMBED_TYPES_STR}, "
                f"but got {type(ref_value).__name__}"
            )
        # add the resolved interpolation value
        if fmt_spec is None:
            parts.append(str(ref_value))
        else:
            parts.append(_format_value(ref_value, fmt_spec))
        last = end
    parts.append(value[last:])  # add the remaining literal part

    return "".join(parts)


def _resolve_path(path: PathKey, state: _State) -> Any:
    if path in state.cache:
        return state.cache[path]

    if path in state.stack:
        chain = " -> ".join(format_path_expr(p) for p in [*state.stack, path])
        raise InterpolationCycleError(f"Interpolation cycle detected: {chain}")

    state.stack.append(path)
    try:
        raw_value = get_by_path(state.raw, path)
        resolved = _resolve_value(raw_value, path, state)
        state.cache[path] = resolved
        return resolved
    finally:
        state.stack.pop()


def _resolve_reference(
    ref_path: PathKey, expr: str, cur_path: PathKey, state: _State
) -> Any:
    try:
        return _resolve_path(ref_path, state)
    except KeyError as exc:
        raise InterpolationUndefinedError(
            f"Undefined interpolation '{expr}' at {format_path_expr(cur_path)}"
        ) from exc


def _format_value(value: Any, fmt_spec: str) -> str:
    """Format a value using the given format specification"""
    if isinstance(value, (date, time, datetime)):
        return value.strftime(fmt_spec)
    return format(value, fmt_spec)


def _split_expr(expr: str) -> tuple[str, str | None]:
    ref, sep, fmt_spec = expr.partition(":")
    ref = ref.strip()
    fmt_spec_opt = fmt_spec if sep else None
    return ref, fmt_spec_opt
