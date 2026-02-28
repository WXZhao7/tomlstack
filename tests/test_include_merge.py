from pathlib import Path

import pytest

from tomlstack import load
from tomlstack.errors import IncludeCycleError, IncludeError, VersionError


def test_include_merge_order_and_current_override(tmp_path: Path) -> None:
    (tmp_path / "a.toml").write_text(
        """
x = 1
[arr]
v = [1, 2]
[db]
host = "a"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "b.toml").write_text(
        """
x = 2
[arr]
v = [3]
[db]
user = "u"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """
include = ["./a.toml", "./b.toml"]
x = 3
[db]
host = "main"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    assert cfg.to_dict() == {
        "x": 3,
        "arr": {"v": [3]},
        "db": {"host": "main", "user": "u"},
    }


def test_relative_include_and_anchor_include(tmp_path: Path) -> None:
    shared = tmp_path / "shared"
    project = tmp_path / "project"
    shared.mkdir()
    project.mkdir()

    (shared / "base.toml").write_text("v = 1\n", encoding="utf-8")
    (project / "local.toml").write_text("w = 2\n", encoding="utf-8")

    (project / "main.toml").write_text(
        """
include = ["./local.toml", "@root/base.toml"]
z = 3

[__meta__.include]
root = "../shared"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(project / "main.toml")
    assert cfg.to_dict() == {"w": 2, "v": 1, "z": 3}


def test_invalid_include_format_error(tmp_path: Path) -> None:
    path = tmp_path / "main.toml"
    path.write_text("include = 'a.toml'\n", encoding="utf-8")

    with pytest.raises(
        IncludeError, match=r"Use ./ or ../ or @label/ or absolute path"
    ):
        load(path)


def test_missing_include_file_error(tmp_path: Path) -> None:
    path = tmp_path / "main.toml"
    path.write_text("include = './missing.toml'\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        load(path)


def test_include_cycle_error_contains_chain(tmp_path: Path) -> None:
    (tmp_path / "a.toml").write_text("include = './b.toml'\n", encoding="utf-8")
    (tmp_path / "b.toml").write_text("include = './a.toml'\n", encoding="utf-8")

    with pytest.raises(IncludeCycleError):
        load(tmp_path / "a.toml")


def test_non_top_level_include_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """
[a]
include = "./x.toml"
v = 1
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    assert cfg.to_dict() == {"a": {"include": "./x.toml", "v": 1}}


def test_meta_root_and_anchor_root_conflict(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """
[__meta__.include]
root = "./a"

[__meta__.include.anchors]
root = "./b"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        IncludeError,
        match=(
            "Conflict between __meta__.include.root and __meta__.include.anchors.root"
        ),
    ):
        load(tmp_path / "main.toml")


def test_unsupported_version(tmp_path: Path) -> None:
    (tmp_path / "a.toml").write_text(
        """
[__meta__]
version = 1
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "b.toml").write_text(
        """
[__meta__]
version = 2
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        "include = ['./a.toml', './b.toml']\n", encoding="utf-8"
    )

    with pytest.raises(VersionError, match="Version conflict when including"):
        load(tmp_path / "main.toml")
