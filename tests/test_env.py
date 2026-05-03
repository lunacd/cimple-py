import os

import cimple.env


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
