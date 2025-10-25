import pytest

from cimple.str_interpolation import interpolate


@pytest.mark.parametrize(
    "input_str,context,result",
    [
        ("abc", {}, "abc"),  # no interpolation
        ("abc ${v} abc", {"v": "aaa"}, "abc aaa abc"),  # use variable
        ("\\${}\\\\", {}, "${}\\"),  # use escape
        ("\\\\${v}\\$", {"v": "abc"}, "\\abc$"),  # use variable + escape
    ],
)
def test_interpolate(input_str: str, context: dict[str, str], result: str):
    assert interpolate(input_str, context) == result


@pytest.mark.parametrize(
    "input_str,context,exception_regex",
    [
        ("abc$", {}, r"Malformed use of variable.*"),  # Dollar without variable
        ("abc$abc", {}, r"Malformed use of variable.*"),  # Variable without curly brace
        ("abc${", {}, r"Malformed use of variable. Cannot find matching }.*"),  # Unclosed variable
        (
            "abc${abc",
            {},
            r"Malformed use of variable. Cannot find matching }.*",
        ),  # Unclosed variable
        ("abc\\.def", {}, r'Invalid escape sequence "\\\.".*'),  # Unknown escape sequence
        ("abc\\", {}, r"Malformed escape sequence.*"),  # Unfinished escape sequence
        ("abc${v}def", {"a": "def"}, r"Undefined variable v."),  # Undefined variable
    ],
)
def test_interpolate_error(input_str: str, context: dict[str, str], exception_regex: str):
    with pytest.raises(RuntimeError, match=exception_regex):
        _ = interpolate(input_str, context)
