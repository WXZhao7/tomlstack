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
from typing import Self

from .base import PathRec, RawToml
from .errors import IncludeError


@dataclass
class IncludeSpec:
    ref: Path  # parent dir of current.toml
    anchors: dict[str, PathRec] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.ref.is_absolute():
            raise ValueError(f"IncludeSpec.ref must be absolute path, got: {self.ref}")

    @staticmethod
    def _include_relative(path: str) -> bool:
        return path.startswith("./") or path.startswith("../")

    @staticmethod
    def _include_absolute(path: str) -> bool:
        return Path(path).is_absolute()

    @staticmethod
    def _include_anchor(path: str) -> bool:
        if not path.startswith("@"):
            return False
        label, sep, value = path[1:].partition("/")
        return bool(label and sep and value)

    @classmethod
    def resolve_anchor_path(cls, ref: Path, anchor_path: str) -> Path:
        if cls._include_relative(anchor_path):
            return (ref / anchor_path).resolve()
        if cls._include_absolute(anchor_path):
            return Path(anchor_path).resolve()
        raise ValueError(
            f"Invalid anchor path: {anchor_path}. "
            "Anchor values must be absolute or start with ./ or ../"
        )

    def resolve_include_path(self, include_path: str) -> Path:
        if self._include_relative(include_path):
            return (self.ref / include_path).resolve()

        if self._include_absolute(include_path):
            return Path(include_path).resolve()

        if self._include_anchor(include_path):
            label, _, rest = include_path[1:].partition("/")
            if label not in self.anchors:
                raise IncludeError(f"Undefined include anchor: {label}")
            return (self.anchors[label].path / rest).resolve()

        raise IncludeError(
            f"Invalid include path format: {include_path}. "
            "Use ./ or ../ or @label/ or absolute path."
        )

    @classmethod
    def from_toml(cls, toml: RawToml) -> Self:
        ref: Path = toml.path.parent

        include = toml.meta.get("include")
        if include is None:
            return cls(ref=ref)
        if not isinstance(include, dict):
            raise IncludeError("Invalid __meta__.include table")

        anchors_raw = include.get("anchors")
        if anchors_raw is None:
            anchors_raw = {}
        if not isinstance(anchors_raw, dict):
            raise IncludeError("Invalid __meta__.include.anchors table")

        anchors: dict[str, PathRec] = {}
        for label, raw_value in anchors_raw.items():
            if not isinstance(label, str) or not isinstance(raw_value, str):
                raise IncludeError("Anchor labels and values must be strings")
            anchors[label] = PathRec(
                raw=raw_value, path=cls.resolve_anchor_path(ref, raw_value)
            )

        # magic root anchor
        if "root" in include:
            root_value = include["root"]
            if not isinstance(root_value, str):
                raise IncludeError("Invalid __meta__.include.root")

            if "root" not in anchors:
                anchors["root"] = PathRec(
                    raw=root_value, path=cls.resolve_anchor_path(ref, root_value)
                )
            else:
                if anchors["root"].raw != root_value:
                    raise IncludeError(
                        "Conflict between __meta__.include.root and "
                        "__meta__.include.anchors.root"
                    )

        return cls(ref=ref, anchors=anchors)
