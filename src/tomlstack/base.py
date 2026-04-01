from dataclasses import dataclass
from pathlib import Path
from typing import Any

PathKey = tuple[str | int, ...]

UNDECLARED_VERSION = 0
SUPPORTED_VERSIONS = {1}


@dataclass(frozen=True, slots=True)
class TomlFile:
    str_: str  # original path
    path: Path  # resolved absolute path


@dataclass(frozen=True, slots=True)
class TomlHist:
    file: TomlFile
    depth: int


@dataclass(frozen=True, slots=True)
class TomlModel:
    metadata: dict[str, Any]
    includes: list[str]
    data: dict[str, Any]
