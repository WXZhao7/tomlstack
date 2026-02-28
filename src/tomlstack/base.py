from dataclasses import dataclass
from pathlib import Path
from typing import Any

PathKey = tuple[str | int, ...]

UNDECLARED_VERSION = 0
SUPPORTED_VERSIONS = {1}


@dataclass(frozen=True, slots=True)
class PathRec:
    raw: str  # original path
    path: Path  # resolved absolute path


@dataclass(frozen=True, slots=True)
class PathHist:
    raw: str
    path: Path
    depth: int


@dataclass(frozen=True, slots=True)
class RawToml:
    path: Path
    meta: dict[str, Any]
    body: dict[str, Any]
    includes: list[str]
