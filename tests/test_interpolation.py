from pathlib import Path

import pytest

from tomlstack import load
from tomlstack.errors import (
    InterpolationCycleError,
    InterpolationError,
    InterpolationUndefinedError,
)


def test_pure_interpolation_keeps_type(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """
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


def test_embedded_interpolation_and_format(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """
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
    out = cfg.to_dict(resolve=True)

    assert out["conn"]["url"] == "postgres://alice:pw@localhost:5432"
    assert out["conn"]["short"] == "   alice"
    assert out["conn"]["day"] == "250102"


def test_undefined_interpolation_raises(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text("x = '${missing.key}'\n", encoding="utf-8")

    cfg = load(tmp_path / "main.toml")
    with pytest.raises(InterpolationUndefinedError, match="Undefined interpolation"):
        cfg.resolve()


def test_interpolation_cycle_raises(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text("a='${b}'\nb='${a}'\n", encoding="utf-8")

    cfg = load(tmp_path / "main.toml")
    with pytest.raises(InterpolationCycleError, match="Interpolation cycle detected"):
        cfg.resolve()


def test_embedded_interpolation_rejects_complex_type(tmp_path: Path) -> None:
    (tmp_path / "main.toml").write_text(
        """
[db]
apps = ["api"]

x = "prefix-${db.apps}"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cfg = load(tmp_path / "main.toml")
    with pytest.raises(InterpolationError, match="Embedded interpolation"):
        cfg.resolve()
