from __future__ import annotations

import re
from typing import Any

from .types import PathKey

# [int]
PURE_INDEX_RE = re.compile(r"\[(\d+)\]")
# str, str[int], str[int][int], ...
VALID_SEGMENT_RE = re.compile(r"([^\[\]]+)((?:\[\d+\])*)$")


def parse_path_expr_match(expr: str) -> PathKey:
    expr = expr.strip()
    if not expr:
        raise ValueError("Empty interpolation path")

    tokens: list[str | int] = []
    segments = expr.split(".")
    if any(not segment for segment in segments):
        raise ValueError(f"Invalid empty key in path '{expr}'")

    for segment in segments:
        match = VALID_SEGMENT_RE.fullmatch(segment)
        if match is None:
            raise ValueError(f"Invalid path segment '{segment}' in path '{expr}'")

        key, indexes = match.groups()
        tokens.append(key)
        tokens.extend(int(index) for index in PURE_INDEX_RE.findall(indexes))

    return tuple(tokens)


def parse_path_expr_scan(expr: str) -> PathKey:
    expr = expr.strip()
    if not expr:
        raise ValueError("Empty interpolation path")

    tokens: list[str | int] = []
    i = 0
    n = len(expr)

    while i < n:
        if expr[i] in ".]":
            raise ValueError(f"Invalid token at position {i} in path '{expr}'")

        start = i
        while i < n and expr[i] not in ".[":
            i += 1
        key = expr[start:i]
        if not key:
            raise ValueError(f"Invalid empty key in path '{expr}'")
        tokens.append(key)

        while i < n and expr[i] == "[":
            i += 1
            idx_start = i
            while i < n and expr[i] != "]":
                i += 1
            if i >= n or expr[i] != "]":
                raise ValueError(f"Unclosed list index in path '{expr}'")
            idx_token = expr[idx_start:i]
            if not idx_token.isdigit():
                raise ValueError(
                    f"List index must be non-negative integer in path '{expr}'"
                )
            tokens.append(int(idx_token))
            i += 1

        if i < n:
            if expr[i] != ".":
                raise ValueError(f"Unexpected token '{expr[i]}' in path '{expr}'")
            i += 1

    return tuple(tokens)


def parse_path_expr(expr: str) -> PathKey:
    """
    Parse a path expression into a tuple of keys.

    Examples:
        "" -> ValueError
        "foo" -> ("foo",)
        "foo.bar" -> ("foo", "bar")
        "foo[0]" -> ("foo", 0)
        "foo.bar[1].baz" -> ("foo", "bar", 1, "baz")
        "foo[0][1]" -> ("foo", 0, 1)

    :param expr: The path expression to parse
    :type expr: str
    :return: The parsed path
    :rtype: PathKey
    """
    return parse_path_expr_match(expr)


def format_path_expr(path: PathKey) -> str:
    """
    Format a path expression as a string.

    Examples:
        () -> "<root>"
        ("foo",) -> "foo"
        ("foo", 0, 1) -> "foo[0][1]"
        ("foo", 0, 1, "bar") -> "foo[0][1].bar"

    :param path: The path to format
    :type path: PathKey
    :return: The formatted path string
    :rtype: str
    """
    if not path:
        return "<root>"

    out = ""
    for part in path:
        if isinstance(part, str):
            if out:
                out += "."
            out += part
        else:
            out += f"[{part}]"
    return out


def get_by_path(data: Any, path: PathKey) -> Any:
    current = data
    passed: list[str | int] = []
    for part in path:
        passed.append(part)
        if isinstance(part, str):
            if not isinstance(current, dict) or part not in current:
                raise KeyError(f"Can't extract {passed!r}")
            current = current[part]
        elif isinstance(part, int):
            if not isinstance(current, list) or part < 0 or part >= len(current):
                raise KeyError(f"Can't extract {passed!r}")
            current = current[part]
        else:
            raise TypeError(f"Invalid path {passed!r}")
    return current
