from dataclasses import dataclass
from pathlib import Path

DataPath = tuple[str | int, ...]

ROOT_PATH: DataPath = ()

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
