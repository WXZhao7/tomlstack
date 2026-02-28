from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from .errors import (
    InterpolationCycleError,
    InterpolationError,
    InterpolationUndefinedError,
)
from .loader import PathKey
from .path_expr import get_by_path, parse_path_expr, path_to_str

EXPR_RE = re.compile(r"\$\{([^{}]+)\}")
ALLOWED_EMBED_TYPES = (str, int, float, date, time, datetime)


@dataclass
class _State:
    raw: dict[str, Any]
    cache: dict[PathKey, Any]
    stack: list[PathKey]


def resolve_interpolations(raw_data: dict[str, Any]) -> dict[str, Any]:
    state = _State(raw=raw_data, cache={}, stack=[])
    return _resolve_value(raw_data, (), state)


def _resolve_path(path: PathKey, state: _State) -> Any:
    if path in state.cache:
        return state.cache[path]
    if path in state.stack:
        chain = " -> ".join(path_to_str(p) for p in [*state.stack, path])
        raise InterpolationCycleError(f"Interpolation cycle detected: {chain}")

    state.stack.append(path)
    try:
        raw_value = get_by_path(state.raw, path)
        resolved = _resolve_value(raw_value, path, state)
        state.cache[path] = resolved
        return resolved
    finally:
        state.stack.pop()


def _resolve_value(value: Any, path: PathKey, state: _State) -> Any:
    if isinstance(value, dict):
        return {k: _resolve_value(v, (*path, k), state) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(v, (*path, i), state) for i, v in enumerate(value)]
    if isinstance(value, str):
        return _resolve_string(value, path, state)
    return value


def _resolve_string(value: str, path: PathKey, state: _State) -> Any:
    matches = list(EXPR_RE.finditer(value))
    if not matches:
        return value

    if len(matches) == 1 and matches[0].span() == (0, len(value)):
        expr = matches[0].group(1)
        ref_path, fmt_spec = _parse_expr(expr, path)
        ref_value = _resolve_reference(ref_path, expr, path, state)
        if fmt_spec is None:
            return ref_value
        return _format_value(ref_value, fmt_spec)

    parts: list[str] = []
    last = 0
    for match in matches:
        start, end = match.span()
        parts.append(value[last:start])

        expr = match.group(1)
        ref_path, fmt_spec = _parse_expr(expr, path)
        ref_value = _resolve_reference(ref_path, expr, path, state)
        if not isinstance(ref_value, ALLOWED_EMBED_TYPES):
            raise InterpolationError(
                f"Embedded interpolation in {path_to_str(path)} "
                "only supports str/int/float/date/time/datetime, "
                f"got {type(ref_value).__name__}"
            )
        if fmt_spec is None:
            parts.append(str(ref_value))
        else:
            parts.append(_format_value(ref_value, fmt_spec))
        last = end

    parts.append(value[last:])
    return "".join(parts)


def _parse_expr(expr: str, path: PathKey) -> tuple[PathKey, str | None]:
    ref, sep, fmt_spec = expr.partition(":")
    ref = ref.strip()
    fmt_spec_opt = fmt_spec if sep else None
    try:
        ref_path = parse_path_expr(ref)
    except ValueError as exc:
        raise InterpolationError(
            f"Invalid interpolation expression '{expr}' at {path_to_str(path)}: {exc}"
        ) from exc
    return ref_path, fmt_spec_opt


def _resolve_reference(
    ref_path: PathKey, expr: str, cur_path: PathKey, state: _State
) -> Any:
    try:
        return _resolve_path(ref_path, state)
    except KeyError as exc:
        raise InterpolationUndefinedError(
            f"Undefined interpolation '{expr}' at {path_to_str(cur_path)}"
        ) from exc


def _format_value(value: Any, fmt_spec: str) -> str:
    if isinstance(value, (date, time, datetime)):
        return value.strftime(fmt_spec)
    return format(value, fmt_spec)
