import os

import pytest

import cimple.env
import cimple.system


@pytest.mark.skipif(
    not cimple.system.is_windows(),
    reason="This test is only relevant for MSVC on Windows",
)
def test_msvc_env():
    # WHEN: getting the MSVC environment variables
    env = cimple.env.get_msvc_envs()

    # THEN: the expected environment variables are present
    assert "INCLUDE" in env
    assert "LIB" in env


def test_baseline_env():
    # WHEN: getting the baseline environment variables
    env = cimple.env.baseline_env()

    # THEN: the expected environment variables are present
    assert "TMP" in env
    assert "SYSTEMROOT" in env
    assert "SYSTEMDRIVE" in env
    assert "Path" in env
    assert "C:\\Windows\\System32\\" in env["Path"]


def test_merge_env():
    # GIVEN: two environment variable dictionaries
    path_env = "Path" if cimple.system.is_windows() else "PATH"
    base_env = {"VAR1": "value1", path_env: "BasePath\\"}
    override_env = {"VAR1": "override_value", "VAR2": "value2", path_env: "OverridePath\\"}

    # WHEN: merging the two environment variable dictionaries
    merged_env = cimple.env.merge_env(base_env, override_env)

    # THEN: the merged environment variable dictionary contains the expected values
    assert merged_env["VAR1"] == "override_value"
    assert merged_env["VAR2"] == "value2"
    assert merged_env[path_env] == f"OverridePath\\{os.pathsep}BasePath\\"


@pytest.mark.skipif(
    not cimple.system.is_windows(),
    reason="This test is only relevant for MSVC on Windows",
)
def test_filter_msvc_path():
    # GIVEN: a PATH string containing MSVC and non-MSVC paths
    msvc_path = "C:\\Program Files\\Microsoft Visual Studio\\18\\Community\\VC\\Tools\\MSVC\\x64"
    non_msvc_path = "C:\\SomeOtherPath"
    full_path = os.pathsep.join([msvc_path, non_msvc_path])

    # WHEN: filtering out MSVC paths
    filtered_path = cimple.env.filter_msvc_path(full_path)

    # THEN: the resulting PATH string only contains non-MSVC paths
    assert non_msvc_path not in filtered_path
    assert msvc_path in filtered_path
