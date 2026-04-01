"""

```toml
__meta__.include.root = "./parent"
# __meta__.include.anchors.root = "./parent
__meta__.include.anchors.project = "/abs/path/project"

include = [
    "./relative.toml",
    "../relative.toml",
    "/abs/path/absolute.toml",
    "@root/anchor.toml",
    "@project/anchor.toml",
]
```

"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

from .base import TomlFile
from .errors import IncludeError


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
    def from_toml(cls, file: TomlFile, metadata: dict[str, Any]) -> Self:
        # ref: Path = file.path.parent

        include = metadata.get("include")
        if include is None:
            return cls(file=file)

        if not isinstance(include, dict):
            raise IncludeError(f"Invalid __meta__.include in {file!r}")

        anchors_raw = include.get("anchors", {})
        if not isinstance(anchors_raw, dict):
            raise IncludeError("Invalid __meta__.include.anchors table")

        anchors: dict[str, TomlFile] = {}
        refpath = file.path.parent
        for label, raw_value in anchors_raw.items():
            if not isinstance(label, str) or not isinstance(raw_value, str):
                raise IncludeError("Anchor labels and values must be strings")
            anchors[label] = TomlFile(
                str_=raw_value, path=cls.resolve_anchor_path(refpath, raw_value)
            )

        # magic root anchor
        if "root" in include:
            root_value = include["root"]
            if not isinstance(root_value, str):
                raise IncludeError("Invalid __meta__.include.root")

            if "root" not in anchors:
                anchors["root"] = TomlFile(
                    str_=root_value, path=cls.resolve_anchor_path(refpath, root_value)
                )
            else:
                if anchors["root"].str_ != root_value:
                    raise IncludeError(
                        "Conflict between __meta__.include.root and "
                        "__meta__.include.anchors.root"
                    )

        return cls(file=file, anchors=anchors)
