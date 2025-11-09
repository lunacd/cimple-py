import pytest

import cimple.env
import cimple.system


@pytest.mark.skipif(
    not cimple.system.is_windows(),
    reason="This test is only relevant for Cygwin paths on Windows",
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
    assert "TEMP" in env
