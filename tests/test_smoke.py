from pathlib import Path

import pytest

from tomlstack import TomlStack, load


def test_load_returns_config(tmp_path: Path) -> None:
    path = tmp_path / "a.toml"
    path.write_text("x = 1\n", encoding="utf-8")

    cfg = load(path)
    assert cfg.to_dict() == {"x": 1}


def test_to_toml_not_implemented(tmp_path: Path) -> None:
    path = tmp_path / "a.toml"
    path.write_text("x = 1\n", encoding="utf-8")

    cfg = load(path)
    try:
        cfg.to_toml()
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Expected NotImplementedError")


def test_toml_stack_cannot_be_constructed_directly() -> None:
    with pytest.raises(TypeError, match="created by load"):
        TomlStack()
