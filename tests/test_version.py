import pytest


from cimple.common.version import version_compare


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
        # Compare revisions
        ("1.0.0-1", "1.0.0-2", -1),
        ("1.0.0-2", "1.0.0-1", 1),
        ("1.0.0-1", "1.0.0-1", 0),
        # Semantic versions overrule revisions
        ("1.0.1-1", "1.0.0-2", 1),
        ("1.0.0-2", "1.0.1-1", -1),
        ("1.0.0-1", "1.0.0-1", 0),
        # Major version overrules minor and patch
        ("2.0.0-1", "1.2.2-2", 1),
        ("0.1.1-1", "1.0.0-2", -1),
        ("1.0.0-1", "1.0.0-1", 0),
    ],
)
def test_version(v1, v2, expected):
    result = version_compare(v1, v2)
    assert result == expected, f"Expected {expected} but got {result} for {v1} vs {v2}"
