from pathlib import Path

import pytest

from tomlstack import TomlNode, load


def test_node_access_origin_and_explain(tmp_path: Path) -> None:
    (tmp_path / "a.toml").write_text(
        """\
[db]
host='a'
""",
        encoding="utf-8",
    )
    (tmp_path / "b.toml").write_text(
        """\
[db]
host='b'
user='u'
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = ['./a.toml','./b.toml']
[db]
host='main'
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    host_node = cfg["db"]["host"]

    assert isinstance(host_node, TomlNode)
    assert host_node.path == ("db", "host")
    assert host_node.raw == "main"
    assert host_node.value == "main"
    # assert host_node.origin == str((tmp_path / "main.toml").resolve())
    assert host_node.history[0].reference == "./a.toml"
    assert host_node.history[0].path == (tmp_path / "a.toml").resolve()
    assert host_node.history[1].reference == "./b.toml"
    assert host_node.history[1].path == (tmp_path / "b.toml").resolve()
    assert host_node.history[2].reference == str(tmp_path / "main.toml")
    assert host_node.history[2].path == (tmp_path / "main.toml").resolve()


def test_list_index_access_and_preview(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """\
[proj]
apps = ['api', 'worker']
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    node = cfg["proj"]["apps"][0]

    assert node.raw == "api"
    assert node.value == "api"
    preview = cfg["proj"].preview()
    assert "apps" in preview
    assert "worker" in preview


def test_to_dict_resolve_flag(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text("x = 1\n", encoding="utf-8")

    cfg = load(tmp_path / "main.toml")
    assert cfg.raw == {"x": 1}
    assert cfg.to_dict() == {"x": 1}


def test_node_raw_returns_an_independent_snapshot(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text("items = [1, 2]\n", encoding="utf-8")

    node = load(tmp_path / "main.toml")["items"]
    raw = node.raw
    raw.append(3)

    assert node.raw == [1, 2]
    assert node[1].raw == 2


def test_toml_node_cannot_be_constructed_directly() -> None:
    with pytest.raises(TypeError, match="TomlStack navigation"):
        TomlNode()
