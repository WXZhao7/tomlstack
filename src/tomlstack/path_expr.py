from __future__ import annotations

from typing import Any

from .loader import PathKey


def parse_path_expr(expr: str) -> PathKey:
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
                raise ValueError(f"List index must be non-negative integer in path '{expr}'")
            tokens.append(int(idx_token))
            i += 1

        if i < n:
            if expr[i] != ".":
                raise ValueError(f"Unexpected token '{expr[i]}' in path '{expr}'")
            i += 1

    return tuple(tokens)


def get_by_path(data: Any, path: PathKey) -> Any:
    cur = data
    for part in path:
        if isinstance(part, str):
            if not isinstance(cur, dict) or part not in cur:
                raise KeyError(part)
            cur = cur[part]
        else:
            if not isinstance(cur, list) or part < 0 or part >= len(cur):
                raise KeyError(part)
            cur = cur[part]
    return cur


def path_to_str(path: PathKey) -> str:
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
