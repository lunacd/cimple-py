import pathlib

import pytest

import cimple.system


@pytest.mark.parametrize(
    "cygwin_path,expected_path",
    [
        # Windows path with backwards slashes
        (
            pathlib.Path("C:\\cygwin\\bin\\bash.exe"),
            pathlib.Path("/cygdrive/c/cygwin/bin/bash.exe"),
        ),
        # Windows path with forward slashes
        (pathlib.Path("D:/cygwin/bin/bash.exe"), pathlib.Path("/cygdrive/d/cygwin/bin/bash.exe")),
        # Unix-style path
        (pathlib.Path("/usr/bin/bash"), pathlib.Path("/usr/bin/bash")),
        # Relative path
        (pathlib.Path("./relative/path"), pathlib.Path("./relative/path")),
    ],
)
@pytest.mark.skipif(
    not cimple.system.platform_name().startswith("windows"),
    reason="This test is only relevant for Cygwin paths on Windows",
)
def test_cygwin_path(cygwin_path, expected_path):
    """
    Test to ensure that the Cygwin path is correctly set up.
    This is a placeholder for actual test logic.
    """
    assert cimple.system.to_cygwin_path(cygwin_path) == expected_path


@pytest.mark.skipif(
    cimple.system.platform_name().startswith("windows"),
    reason="This test is only for non-Windows systems",
)
def test_cygwin_path_is_no_op_on_posix():
    """
    Test to ensure that the Cygwin path conversion is a no-op on non-Windows systems.
    """
    posix_path = pathlib.Path("/usr/local/bin/bash")
    assert cimple.system.to_cygwin_path(posix_path) == posix_path
