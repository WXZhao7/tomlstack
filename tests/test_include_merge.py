from pathlib import Path

import pytest

from tomlstack import load
from tomlstack.errors import IncludeCycleError, IncludeError


def test_include_merge_order_and_current_override(tmp_path: Path) -> None:
    (tmp_path / "a.toml").write_text(
        """\
x = 1
[arr]
v = [1, 2]
[db]
host = "a"
""",
        encoding="utf-8",
    )
    (tmp_path / "b.toml").write_text(
        """\
x = 2
[arr]
v = [3]
[db]
user = "u"
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = ["./a.toml", "./b.toml"]
x = 3
[db]
host = "main"
""",
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
        """\
items = ['base-0', 'base-1']
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = './base.toml'
items = ['main-0']
""",
        encoding="utf-8",
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
        """\
[value]
old = 'base'
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = './base.toml'
value = 'main'
""",
        encoding="utf-8",
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
    (tmp_path / "base.toml").write_text(
        """\
value = 'base'
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = './base.toml'
[value]
new = 'main'
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")

    assert [hist.file.str_ for hist in cfg["value"].history] == [
        "./base.toml",
        str(tmp_path / "main.toml"),
    ]
    assert [hist.file.str_ for hist in cfg["value"]["new"].history] == [
        str(tmp_path / "main.toml")
    ]


def test_recursive_table_merge_tracks_only_files_that_define_each_path(
    tmp_path: Path,
) -> None:
    (tmp_path / "base.toml").write_text(
        """\
[service]
host = 'base'
[service.auth]
user = 'base-user'
""",
        encoding="utf-8",
    )
    (tmp_path / "overlay.toml").write_text(
        """\
[service]
host = 'overlay'
[service.auth]
password = 'secret'
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = ['./base.toml', './overlay.toml']
[service]
port = 8080
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")

    assert cfg.to_dict(resolve=False) == {
        "service": {
            "host": "overlay",
            "auth": {"user": "base-user", "password": "secret"},
            "port": 8080,
        }
    }
    assert [item.file.str_ for item in cfg["service"].history] == [
        "./base.toml",
        "./overlay.toml",
        str(tmp_path / "main.toml"),
    ]
    assert [item.file.str_ for item in cfg["service"]["host"].history] == [
        "./base.toml",
        "./overlay.toml",
    ]
    assert [item.file.str_ for item in cfg["service"]["auth"]["user"].history] == [
        "./base.toml"
    ]
    assert [item.file.str_ for item in cfg["service"]["auth"]["password"].history] == [
        "./overlay.toml"
    ]
    assert [item.file.str_ for item in cfg["service"]["port"].history] == [
        str(tmp_path / "main.toml")
    ]


def test_multiple_type_replacements_discard_all_obsolete_descendants(
    tmp_path: Path,
) -> None:
    (tmp_path / "base.toml").write_text(
        """\
[value]
obsolete = 'base'
""",
        encoding="utf-8",
    )
    (tmp_path / "middle.toml").write_text(
        """\
include = './base.toml'
value = 'middle'
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = './middle.toml'
[value]
current = 'main'
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")

    assert cfg["value"].raw == {"current": "main"}
    assert [item.file.str_ for item in cfg["value"].history] == [
        "./base.toml",
        "./middle.toml",
        str(tmp_path / "main.toml"),
    ]
    assert [item.file.str_ for item in cfg["value"]["current"].history] == [
        str(tmp_path / "main.toml")
    ]
    with pytest.raises(KeyError):
        cfg["value"]["obsolete"]


def test_empty_table_updates_parent_history_without_replacing_children(
    tmp_path: Path,
) -> None:
    (tmp_path / "base.toml").write_text(
        """\
[service]
host = 'base'
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = './base.toml'
[service]
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")

    assert cfg["service"].raw == {"host": "base"}
    assert [item.file.str_ for item in cfg["service"].history] == [
        "./base.toml",
        str(tmp_path / "main.toml"),
    ]
    assert [item.file.str_ for item in cfg["service"]["host"].history] == [
        "./base.toml"
    ]


def test_same_file_loaded_through_two_branches_records_both_occurrences(
    tmp_path: Path,
) -> None:
    (tmp_path / "shared.toml").write_text(
        """\
value = 1
""",
        encoding="utf-8",
    )
    (tmp_path / "a.toml").write_text(
        """\
include = './shared.toml'
a = true
""",
        encoding="utf-8",
    )
    (tmp_path / "b.toml").write_text(
        """\
include = './shared.toml'
b = true
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = ['./a.toml', './b.toml']
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")

    assert cfg.to_dict() == {"value": 1, "a": True, "b": True}
    assert [item.file.str_ for item in cfg["value"].history] == [
        "./shared.toml",
        "./shared.toml",
    ]
    assert [item.depth for item in cfg["value"].history] == [3, 3]


def test_relative_include_and_anchor_include(tmp_path: Path) -> None:
    shared = tmp_path / "shared"
    project = tmp_path / "project"
    shared.mkdir()
    project.mkdir()

    (shared / "base.toml").write_text(
        """\
v = 1
""",
        encoding="utf-8",
    )
    (project / "local.toml").write_text(
        """\
w = 2
""",
        encoding="utf-8",
    )

    (project / "main.toml").write_text(
        """\
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
        """\
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
    (tmp_path / "a.toml").write_text(
        """\
include = './b.toml'
""",
        encoding="utf-8",
    )
    (tmp_path / "b.toml").write_text(
        """\
include = './a.toml'
""",
        encoding="utf-8",
    )

    with pytest.raises(IncludeCycleError):
        load(tmp_path / "a.toml")


def test_non_top_level_include_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """\
[a]
include = "./x.toml"
v = 1
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    assert cfg.to_dict() == {"a": {"include": "./x.toml", "v": 1}}
