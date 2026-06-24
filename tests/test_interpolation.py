from pathlib import Path

import pytest

from tomlstack import InterpolationDependency, ResolutionTrace, load
from tomlstack.errors import (
    InterpolationCycleError,
    InterpolationError,
    InterpolationUndefinedError,
)


def test_pure_interpolation_keeps_type(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """\
[db]
port = 5432
apps = ["api", "worker"]

[p]
port = "${db.port}"
app0 = "${db.apps[0]}"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    cfg.resolve()
    d = cfg.to_dict()

    assert d["p"]["port"] == 5432
    assert isinstance(d["p"]["port"], int)
    assert d["p"]["app0"] == "api"


def test_interpolation_keeps_expression_provenance(tmp_path: Path) -> None:
    (tmp_path / "base.toml").write_text(
        """\
source = 42
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = './base.toml'
target = '${source}'
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")

    assert cfg["target"].raw == "${source}"
    assert cfg["target"].value == 42
    assert cfg["target"].origin.reference == str(tmp_path / "main.toml")
    assert cfg["source"].origin.reference == "./base.toml"


def test_replace_dependency_keeps_target_history_separate(tmp_path: Path) -> None:
    (tmp_path / "base.toml").write_text("source = 1\n", encoding="utf-8")
    (tmp_path / "prod.toml").write_text("source = 2\n", encoding="utf-8")
    (tmp_path / "main.toml").write_text(
        """\
include = ['./base.toml', './prod.toml']
target = '${source}'
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    target = cfg["target"]

    assert target.value == 2
    assert [item.reference for item in target.history] == [str(tmp_path / "main.toml")]
    dependency = target.dependencies[0]
    assert isinstance(dependency, InterpolationDependency)
    assert dependency.target_path == ("target",)
    assert dependency.source_path == ("source",)
    assert dependency.expression == "${source}"
    assert dependency.kind == "replace"
    assert dependency.format_spec is None
    assert [item.reference for item in dependency.source_history] == [
        "./base.toml",
        "./prod.toml",
    ]
    trace = target.explain()
    assert isinstance(trace, ResolutionTrace)
    assert [node.path for node in trace.nodes] == [("target",), ("source",)]
    assert trace.dependencies == target.dependencies


def test_embed_and_format_dependencies_preserve_expression_order(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.toml").write_text(
        """\
host = 'db'
port = 42
url = 'tcp://${host}:${port:05d}'
formatted = '${port:05d}'
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")

    url_dependencies = [
        (item.expression, item.kind, item.format_spec)
        for item in cfg["url"].dependencies
    ]
    assert url_dependencies == [
        ("${host}", "embed", None),
        ("${port:05d}", "embed", "05d"),
    ]
    formatted_dependencies = [
        (item.expression, item.kind, item.format_spec)
        for item in cfg["formatted"].dependencies
    ]
    assert formatted_dependencies == [
        ("${port:05d}", "format", "05d"),
    ]


def test_explain_follows_chained_dependencies(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """\
c = 7
b = '${c}'
a = '${b}'
""",
        encoding="utf-8",
    )

    trace = load(tmp_path / "main.toml")["a"].explain()

    assert [node.path for node in trace.nodes] == [("a",), ("b",), ("c",)]
    assert [(item.target_path, item.source_path) for item in trace.dependencies] == [
        (("a",), ("b",)),
        (("b",), ("c",)),
    ]


def test_explain_descends_into_fully_replaced_container(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """\
base = 'value'
target = '${source}'
[source]
part = '${base}'
plain = 1
""",
        encoding="utf-8",
    )

    target = load(tmp_path / "main.toml")["target"]
    trace = target.explain()

    assert target.value == {"part": "value", "plain": 1}
    assert [node.path for node in trace.nodes] == [
        ("target",),
        ("source",),
        ("source", "part"),
        ("base",),
    ]
    assert [(item.target_path, item.source_path) for item in trace.dependencies] == [
        (("target",), ("source",)),
        (("source", "part"), ("base",)),
    ]
    with pytest.raises(TypeError):
        target["part"]


def test_node_without_interpolation_has_empty_dependency_trace(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text("value = 1\n", encoding="utf-8")

    node = load(tmp_path / "main.toml")["value"]

    assert node.dependencies == ()
    assert node.explain().nodes[0].path == ("value",)
    assert node.explain().dependencies == ()


def test_interpolation_reads_final_overridden_value(tmp_path: Path) -> None:
    (tmp_path / "base.toml").write_text(
        """\
port = 1000
""",
        encoding="utf-8",
    )
    (tmp_path / "prod.toml").write_text(
        """\
port = 2000
""",
        encoding="utf-8",
    )
    (tmp_path / "main.toml").write_text(
        """\
include = ['./base.toml', './prod.toml']
url = 'port=${port}'
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")

    assert cfg["url"].value == "port=2000"
    assert [item.reference for item in cfg["port"].history] == [
        "./base.toml",
        "./prod.toml",
    ]
    assert cfg["url"].origin.reference == str(tmp_path / "main.toml")


def test_full_interpolation_of_complex_values_does_not_alias_results(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.toml").write_text(
        """\
source = [1, 2]
first = '${source}'
second = '${source}'
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    result = cfg.to_dict()

    assert result == {"source": [1, 2], "first": [1, 2], "second": [1, 2]}
    assert result["source"] is not result["first"]
    assert result["first"] is not result["second"]


def test_embedded_interpolation_and_format(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """\
[db]
user = "alice"
pass = "pw"
host = "localhost"
port = 5432
stamp = 2025-01-02

[conn]
url = "postgres://${db.user}:${db.pass}@${db.host}:${db.port}"
short = "${db.user:>8s}"
day = "${db.stamp:%y%m%d}"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    out = cfg.to_dict()

    assert out["conn"]["url"] == "postgres://alice:pw@localhost:5432"
    assert out["conn"]["short"] == "   alice"
    assert out["conn"]["day"] == "250102"


def test_undefined_interpolation_raises(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """\
x = '${missing.key}'
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    with pytest.raises(InterpolationUndefinedError):
        cfg.resolve()
    assert cfg._resolution is None

    with pytest.raises(InterpolationUndefinedError):
        cfg.resolve()


def test_interpolation_cycle_raises(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """\
a = '${b}'
b = '${a}'
""",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    with pytest.raises(InterpolationCycleError):
        cfg.resolve()


def test_invalid_interpolation_path_raises_interpolation_error(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        "x = '${missing..key}'\n", encoding="utf-8"
    )

    with pytest.raises(InterpolationError, match="Invalid interpolation path"):
        load(tmp_path / "main.toml").resolve()


def test_embedded_interpolation_rejects_complex_type(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """\
[db]
apps = ["api"]

x = "prefix-${db.apps}"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    with pytest.raises(InterpolationError, match="Cannot format value of type list"):
        cfg.resolve()
