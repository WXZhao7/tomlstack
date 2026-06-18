from dataclasses import dataclass
from pathlib import Path

DataPath = tuple[str | int, ...]

CONFIG_TABLE = "tomlstack"
ROOT_PATH: DataPath = ()


@dataclass(frozen=True, slots=True)
class TomlFile:
    str_: str  # original path
    path: Path  # resolved absolute path


@dataclass(frozen=True, slots=True)
class TomlHist:
    file: TomlFile
    depth: int
