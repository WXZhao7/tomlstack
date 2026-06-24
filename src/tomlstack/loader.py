from __future__ import annotations

import tomllib
from contextlib import contextmanager
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any

from .errors import ContentError, IncludeCycleError, TomlFormatError
from .include import _IncludeResolver
from .tree import _DataNode, _DataNodeValue
from .types import CONFIG_TABLE, IncludeNode, TomlFile


@dataclass(frozen=True, slots=True)
class _ParsedToml:
    includes: list[str]
    anchors: dict[str, str]
    data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _LoadedToml:
    root: _DataNode
    include_tree: IncludeNode


@dataclass
class _LoadContext:
    file_stack: list[TomlFile] = field(default_factory=list)
    # current include stack for cycle detection

    def _render_include_chain(self) -> str:
        return "\n".join(
            f"\t{file.reference} -> {file.path}" for file in self.file_stack
        )

    @contextmanager
    def enter_file(self, entry: TomlFile):
        self._validate_cycle_include(entry)
        toml = _parse_raw_file(entry.path)

        self.file_stack.append(entry)
        try:
            yield toml
        finally:
            self.file_stack.pop()

    def _validate_cycle_include(self, entry: TomlFile) -> None:

        def render_cycle_include() -> str:
            msg = f"Include cycle detected when load {self.file_stack[0].reference!r}\n"
            for file in self.file_stack + [entry]:
                if file.path == entry.path:
                    msg += f"\t=> {file.reference} -> {file.path}\n"
                else:
                    msg += f"\t   {file.reference} -> {file.path}\n"
            return msg

        for file in self.file_stack:
            if file.path == entry.path:
                raise IncludeCycleError(render_cycle_include())


def _load_toml_with_includes(
    root_file: str | PathLike[str],
) -> _LoadedToml:
    abs_path = Path(root_file).expanduser().resolve()
    return _load_file(
        TomlFile(reference=str(root_file), path=abs_path), _LoadContext()
    )


def _load_file(entry: TomlFile, ctx: _LoadContext) -> _LoadedToml:

    with ctx.enter_file(entry) as toml:
        current = _annotate(toml.data, entry)
        # Includes are merged in order; later includes override earlier ones.
        # The current file has the highest precedence.
        include_resolver = _IncludeResolver.from_toml(entry, toml.anchors)
        merged = _DataNode(value={}, history=())
        children: list[IncludeNode] = []
        for raw_path in toml.includes:
            abs_path = include_resolver.resolve_include_path(raw_path)
            included = _load_file(
                TomlFile(reference=raw_path, path=abs_path), ctx
            )
            merged = _merge_nodes(merged, included.root)
            children.append(included.include_tree)
        return _LoadedToml(
            root=_merge_nodes(merged, current),
            include_tree=IncludeNode(file=entry, children=tuple(children)),
        )


def _annotate(value: Any, file: TomlFile) -> _DataNode:
    annotated: _DataNodeValue
    if isinstance(value, dict):
        annotated = {key: _annotate(child, file) for key, child in value.items()}
    elif isinstance(value, list):
        annotated = [_annotate(child, file) for child in value]
    else:
        annotated = value
    return _DataNode(value=annotated, history=(file,))


def _merge_nodes(low: _DataNode, high: _DataNode) -> _DataNode:
    """Merge two nodes with high priority overriding low priority."""
    history = low.history + high.history
    if isinstance(low.value, dict) and isinstance(high.value, dict):
        merged = dict(low.value)
        for key, high_child in high.value.items():
            if key in merged:
                merged[key] = _merge_nodes(merged[key], high_child)
            else:
                merged[key] = high_child
        return _DataNode(value=merged, history=history)
    return _DataNode(value=high.value, history=history)


def _parse_raw_file(path: Path) -> _ParsedToml:
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise TomlFormatError(f"Invalid TOML in {path}") from exc

    metadata = data.pop(CONFIG_TABLE, {})
    if not isinstance(metadata, dict):
        raise ContentError(f"Invalid {CONFIG_TABLE} table in {path}")

    includes: list[str] = []
    raw_include = data.pop("include", None)

    if raw_include is None:
        pass
    elif isinstance(raw_include, str):
        includes.append(raw_include)
    elif isinstance(raw_include, list):
        for item in raw_include:
            if not isinstance(item, str):
                raise ContentError(f"Invalid include item {item!r} in {path}")
        includes.extend(raw_include)
    else:
        raise ContentError(f"Invalid include specification in {path}")

    anchors: dict[str, str] = {}
    raw_anchors = metadata.get("anchors", None)
    if raw_anchors is None:
        pass
    elif isinstance(raw_anchors, dict):
        for label, value in raw_anchors.items():
            if not isinstance(value, str):
                raise ContentError(f"Invalid anchor {label!r} -> {value!r} in {path}")
            anchors[label] = value
    else:
        raise ContentError(f"Invalid anchors specification in {path}")

    return _ParsedToml(includes=includes, anchors=anchors, data=data)
