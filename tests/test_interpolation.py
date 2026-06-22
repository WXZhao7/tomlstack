from pathlib import Path

import pytest

from tomlstack import load
from tomlstack.errors import (
    InterpolationError,
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
    assert cfg["target"].origin.file.str_ == str(tmp_path / "main.toml")
    assert cfg["source"].origin.file.str_ == "./base.toml"


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
    assert [item.file.str_ for item in cfg["port"].history] == [
        "./base.toml",
        "./prod.toml",
    ]
    assert cfg["url"].origin.file.str_ == str(tmp_path / "main.toml")


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
    with pytest.raises(InterpolationError):
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
    with pytest.raises(InterpolationError):
        cfg.resolve()


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
    with pytest.raises(InterpolationError, match="Failed to resolve"):
        cfg.resolve()
