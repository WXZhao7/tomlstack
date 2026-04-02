from __future__ import annotations

import re
from typing import Any

from .errors import DataPathError
from .types import ROOT_PATH, DataPath

# [int]
PURE_INDEX_RE = re.compile(r"\[(\d+)\]")
# str, str[int], str[int][int], ...
VALID_SEGMENT_RE = re.compile(r"([^\[\]]+)((?:\[\d+\])*)$")


def parse_path_expr_match(expr: str) -> DataPath:

    if not expr:
        raise DataPathError("Empty interpolation path")

    if any(c.isspace() for c in expr):
        raise DataPathError(f"Path expression cannot contain whitespace: {expr!r}")

    tokens: list[str | int] = []
    segments = expr.split(".")
    if any(not segment for segment in segments):
        raise DataPathError(f"Invalid empty key in path {expr!r}")

    for segment in segments:
        match = VALID_SEGMENT_RE.fullmatch(segment)
        if match is None:
            raise DataPathError(f"Invalid path segment {segment!r} in path {expr!r}")

        key, indexes = match.groups()
        tokens.append(key)
        tokens.extend(int(index) for index in PURE_INDEX_RE.findall(indexes))

    return tuple(tokens)


def parse_path_expr_scan(expr: str) -> DataPath:
    if not expr:
        raise DataPathError("Empty interpolation path")

    if any(c.isspace() for c in expr):
        raise DataPathError(f"Path expression cannot contain whitespace: {expr!r}")

    tokens: list[str | int] = []
    i = 0
    n = len(expr)

    while i < n:
        if expr[i] in ".]":
            raise DataPathError(f"Invalid token at position {i} in path {expr!r}")

        start = i
        while i < n and expr[i] not in ".[":
            i += 1
        key = expr[start:i]
        if not key:
            raise DataPathError(f"Invalid empty key in path {expr!r}")
        tokens.append(key)

        while i < n and expr[i] == "[":
            i += 1
            idx_start = i
            while i < n and expr[i] != "]":
                i += 1
            if i >= n or expr[i] != "]":
                raise DataPathError(f"Unclosed list index in path {expr!r}")
            idx_token = expr[idx_start:i]
            if not idx_token.isdigit():
                raise DataPathError(
                    f"List index must be non-negative integer in path {expr!r}"
                )
            tokens.append(int(idx_token))
            i += 1

        if i < n:
            if expr[i] != ".":
                raise DataPathError(f"Unexpected token '{expr[i]}' in path {expr!r}")
            i += 1

    return tuple(tokens)


def parse_path_expr(expr: str) -> DataPath:
    """
    Parse a path expression into a tuple of keys.

    Examples:
        "" -> DataPathError
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


def format_path_expr(path: DataPath) -> str:
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
    if path == ROOT_PATH:
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


def get_by_path(data: Any, path: DataPath) -> Any:
    cur_data = data
    cur_path = []
    for part in path:
        cur_path.append(part)
        if isinstance(part, str):
            if not isinstance(cur_data, dict) or part not in cur_data:
                raise DataPathError(
                    f"Key {part!r} not found when accessing "
                    f"{format_path_expr(tuple(cur_path))!r}"
                )
            cur_data = cur_data[part]
        elif isinstance(part, int):
            if not isinstance(cur_data, list) or part < 0 or part >= len(cur_data):
                raise DataPathError(
                    f"Index {part!r} out of bounds "
                    f"when accessing {format_path_expr(tuple(cur_path))!r}"
                )
            cur_data = cur_data[part]
        else:
            raise TypeError(
                f"Invalid path part {part!r} "
                f"when accessing {format_path_expr(tuple(cur_path))!r}"
            )
    return cur_data
