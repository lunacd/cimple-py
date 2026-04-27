import os

import pytest

import cimple.env
import cimple.system


@pytest.mark.skipif(
    not cimple.system.is_windows(),
    reason="This test is only relevant for Windows",
)
def test_window_baseline_env():
    # WHEN: getting the baseline environment variables
    env = cimple.env.baseline_env()

    # THEN: the expected environment variables are present
    assert "TMP" in env
    assert "TEMP" in env
    assert "TMPDIR" in env
    assert "SYSTEMROOT" in env
    assert "SYSTEMDRIVE" in env
    assert "PATH" in env

    # Windows paths are case-insensitive, normalize to uppercase for assertion
    assert "C:\\WINDOWS\\SYSTEM32" in env["PATH"].upper()


@pytest.mark.skipif(
    cimple.system.is_windows(),
    reason="This test is only relevant for Unix-like systems",
)
def test_unix_baseline_env():
    # WHEN: getting the baseline environment variables
    env = cimple.env.baseline_env()

    # THEN: the expected environment variables are present
    assert "TMP" in env
    assert "TEMP" in env
    assert "TMPDIR" in env
    assert "PATH" in env


def test_merge_env():
    # GIVEN: two environment variable dictionaries
    base_env = {"VAR1": "value1", "PATH": "BasePath\\"}
    override_env = {"VAR1": "override_value", "VAR2": "value2", "PATH": "OverridePath\\"}

    # WHEN: merging the two environment variable dictionaries
    merged_env = cimple.env.merge_env(base_env, override_env)

    # THEN: the merged environment variable dictionary contains the expected values
    assert merged_env["VAR1"] == "override_value"
    assert merged_env["VAR2"] == "value2"
    assert merged_env["PATH"] == f"OverridePath\\{os.pathsep}BasePath\\"
