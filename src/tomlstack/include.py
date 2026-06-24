from dataclasses import dataclass
from pathlib import Path
from typing import Self

from .errors import IncludeError
from .types import TomlFile


@dataclass
class _IncludeResolver:
    including_file: TomlFile
    anchor_roots: dict[str, Path]

    @staticmethod
    def _is_relative(path: str) -> bool:
        return path.startswith("./") or path.startswith("../")

    @staticmethod
    def _is_absolute(path: str) -> bool:
        return Path(path).is_absolute()

    @staticmethod
    def _is_anchor_path(path: str) -> bool:
        if not path.startswith("@"):
            return False
        label, sep, value = path[1:].partition("/")
        return bool(label and sep and value)

    @classmethod
    def resolve_anchor_path(cls, base_dir: Path, anchor_path: str) -> Path:
        if cls._is_absolute(anchor_path):
            return Path(anchor_path).resolve()
        if cls._is_relative(anchor_path):
            return (base_dir / anchor_path).resolve()
        raise IncludeError(
            f"Invalid anchor path: {anchor_path}. "
            "Anchor values must be absolute or start with ./ or ../"
        )

    def resolve_include_path(self, include_path: str) -> Path:
        if self._is_absolute(include_path):
            return Path(include_path).resolve()

        if self._is_relative(include_path):
            return (self.including_file.path.parent / include_path).resolve()

        if self._is_anchor_path(include_path):
            label, _, rest = include_path[1:].partition("/")
            if label not in self.anchor_roots:
                raise IncludeError(f"Undefined include anchor: {label}")
            return (self.anchor_roots[label] / rest).resolve()

        raise IncludeError(
            f"Invalid include path format: {include_path}. "
            "Use ./ or ../ or @label/ or absolute path."
        )

    @classmethod
    def from_toml(cls, file: TomlFile, raw_anchors: dict[str, str]) -> Self:
        anchor_roots: dict[str, Path] = {}
        base_dir = file.path.parent

        for label, raw_value in raw_anchors.items():
            anchor_roots[label] = cls.resolve_anchor_path(base_dir, raw_value)

        return cls(including_file=file, anchor_roots=anchor_roots)
