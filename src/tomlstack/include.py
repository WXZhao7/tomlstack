from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from .errors import IncludeError
from .types import TomlFile


@dataclass
class IncludeSpec:
    file: TomlFile  # parent dir of current.toml
    anchors: dict[str, TomlFile] = field(default_factory=dict)

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
    def resolve_anchor_path(cls, ref_path: Path, anchor_path: str) -> Path:
        if cls._is_absolute(anchor_path):
            return Path(anchor_path).resolve()
        if cls._is_relative(anchor_path):
            return (ref_path / anchor_path).resolve()
        raise ValueError(
            f"Invalid anchor path: {anchor_path}. "
            "Anchor values must be absolute or start with ./ or ../"
        )

    def resolve_include_path(self, include_path: str) -> Path:
        if self._is_absolute(include_path):
            return Path(include_path).resolve()

        if self._is_relative(include_path):
            return (self.file.path.parent / include_path).resolve()

        if self._is_anchor_path(include_path):
            label, _, rest = include_path[1:].partition("/")
            if label not in self.anchors:
                raise IncludeError(f"Undefined include anchor: {label}")
            return (self.anchors[label].path / rest).resolve()

        raise IncludeError(
            f"Invalid include path format: {include_path}. "
            "Use ./ or ../ or @label/ or absolute path."
        )

    @classmethod
    def from_toml(cls, file: TomlFile, raw_anchors: dict[str, str]) -> Self:
        anchors: dict[str, TomlFile] = {}
        ref_path = file.path.parent

        for label, raw_value in raw_anchors.items():
            anchors[label] = TomlFile(
                str_=raw_value, path=cls.resolve_anchor_path(ref_path, raw_value)
            )

        return cls(file=file, anchors=anchors)
