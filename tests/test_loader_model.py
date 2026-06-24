from pathlib import Path

from tomlstack.loader import load_toml_with_includes
from tomlstack.tree import _DataNode


def test_loaded_tree_recursively_binds_every_value_to_history(tmp_path: Path) -> None:
    path = tmp_path / "main.toml"
    path.write_text(
        """\
title = 'demo'
[service]
ports = [8000, 8001]
""",
        encoding="utf-8",
    )

    root = load_toml_with_includes(path).root

    def assert_node_tree(node: _DataNode) -> None:
        assert isinstance(node.history, tuple)
        assert node.history
        if isinstance(node.value, dict):
            assert all(isinstance(child, _DataNode) for child in node.value.values())
            for child in node.value.values():
                assert_node_tree(child)
        elif isinstance(node.value, list):
            assert all(isinstance(child, _DataNode) for child in node.value)
            for child in node.value:
                assert_node_tree(child)

    assert_node_tree(root)
