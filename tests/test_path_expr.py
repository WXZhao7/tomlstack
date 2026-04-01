import pytest

from tomlstack.path_expr import parse_path_expr_match, parse_path_expr_scan


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("a", ("a",)),
        ("a.b.c", ("a", "b", "c")),
        ("a.b.c[1]", ("a", "b", "c", 1)),
        ("a.b[1][2]", ("a", "b", 1, 2)),
        ("a[0][1].b", ("a", 0, 1, "b")),
        ("  db.apps[0]  ", ("db", "apps", 0)),
    ],
)
def test_parse_path_expr_re_valid(expr: str, expected: tuple[str | int, ...]) -> None:
    assert parse_path_expr_match(expr) == expected


@pytest.mark.parametrize(
    "expr",
    [
        "",
        "   ",
        ".a",
        "a.",
        "a..b",
        "[0]",
        "a[]",
        "a[foo]",
        "a[1",
        "a]",
        "a[1]x",
        "a[[1]]",
    ],
)
def test_parse_path_expr_re_invalid(expr: str) -> None:
    with pytest.raises(ValueError):
        parse_path_expr_match(expr)


@pytest.mark.parametrize(
    "expr",
    [
        "a",
        "a.b.c",
        "a.b.c[1]",
        "a.b[1][2]",
        "a[0][1].b",
        "db.apps[0]",
    ],
)
def test_parse_path_expr_re_matches_original_on_supported_inputs(expr: str) -> None:
    assert parse_path_expr_match(expr) == parse_path_expr_scan(expr)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ((), "<root>"),
        (("foo",), "foo"),
        (("foo", 0, 1), "foo[0][1]"),
        (("foo", 0, 1, "bar"), "foo[0][1].bar"),
    ],
)
def test_format_path_expr(path: tuple[str | int, ...], expected: str) -> None:
    from tomlstack.path_expr import format_path_expr

    assert format_path_expr(path) == expected
