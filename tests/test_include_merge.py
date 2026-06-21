from pathlib import Path

import pytest

from tomlstack import load
from tomlstack.errors import IncludeCycleError, IncludeError


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


def test_replacing_list_discards_replaced_element_history(tmp_path: Path) -> None:
    (tmp_path / "base.toml").write_text(
        "items = ['base-0', 'base-1']\n", encoding="utf-8"
    )
    (tmp_path / "main.toml").write_text(
        "include = './base.toml'\nitems = ['main-0']\n", encoding="utf-8"
    )

    cfg = load(tmp_path / "main.toml")

    assert cfg["items"].raw == ["main-0"]
    assert [hist.file.str_ for hist in cfg["items"].history] == [
        "./base.toml",
        str(tmp_path / "main.toml"),
    ]
    assert [hist.file.str_ for hist in cfg["items"][0].history] == [
        str(tmp_path / "main.toml")
    ]
    with pytest.raises(IndexError):
        cfg["items"][1]


def test_replacing_table_discards_replaced_child_history(tmp_path: Path) -> None:
    (tmp_path / "base.toml").write_text(
        "[value]\nold = 'base'\n", encoding="utf-8"
    )
    (tmp_path / "main.toml").write_text(
        "include = './base.toml'\nvalue = 'main'\n", encoding="utf-8"
    )

    cfg = load(tmp_path / "main.toml")

    assert cfg["value"].raw == "main"
    assert [hist.file.str_ for hist in cfg["value"].history] == [
        "./base.toml",
        str(tmp_path / "main.toml"),
    ]
    with pytest.raises(TypeError):
        cfg["value"]["old"]


def test_replacing_scalar_with_table_keeps_only_new_child_history(
    tmp_path: Path,
) -> None:
    (tmp_path / "base.toml").write_text("value = 'base'\n", encoding="utf-8")
    (tmp_path / "main.toml").write_text(
        "include = './base.toml'\n[value]\nnew = 'main'\n", encoding="utf-8"
    )

    cfg = load(tmp_path / "main.toml")

    assert [hist.file.str_ for hist in cfg["value"].history] == [
        "./base.toml",
        str(tmp_path / "main.toml"),
    ]
    assert [hist.file.str_ for hist in cfg["value"]["new"].history] == [
        str(tmp_path / "main.toml")
    ]


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

[tomlstack.anchors]
root = "../shared"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(project / "main.toml")
    assert cfg.to_dict() == {"w": 2, "v": 1, "z": 3}


def test_tomlstack_table_is_configuration_not_data(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """
x = 1

[tomlstack]
version = 1

[app]
name = "demo"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    assert cfg.to_dict() == {"x": 1, "app": {"name": "demo"}}


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
