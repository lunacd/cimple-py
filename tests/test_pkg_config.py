import os
import pathlib

import pytest

import cimple.models.pkg
import cimple.models.pkg_config


def test_load_pkg_config(cimple_pi: pathlib.Path):
    # GIVEN: a basic simple store
    # WHEN: loading a pkg config
    pkg_config = cimple.models.pkg_config.load_pkg_config(
        cimple_pi, cimple.models.pkg.SrcPkgId("pkg1"), "2.0-1"
    )

    # THEN: the pkg config is loaded correctly
    assert pkg_config.id == cimple.models.pkg.SrcPkgId("pkg1")
    assert pkg_config.version == "2.0-1"


def test_load_pkg_config_bootstrap(cimple_pi: pathlib.Path):
    # GIVEN: a basic simple store
    # WHEN: loading a pkg config
    pkg_config = cimple.models.pkg_config.load_pkg_config(
        cimple_pi, cimple.models.pkg.SrcPkgId("bootstrap:bootstrap1"), "1.0.0-1"
    )

    # THEN: the pkg config is loaded correctly
    assert pkg_config.id == cimple.models.pkg.SrcPkgId("bootstrap1")
    assert pkg_config.version == "1.0.0-1"


@pytest.mark.parametrize(
    "rules,default_cwd,builtin_variables,bin_paths,expected_rules",
    [
        # Simple rule
        (
            cimple.models.pkg_config.PkgConfigRulesSection(
                default=["echo hello", "echo hello again"]
            ),
            pathlib.Path("/default"),
            {},
            [],
            cimple.models.pkg_config.PkgConfigNormalizedRulesList.model_construct(
                [
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={},
                        rule=["echo", "hello"],
                    ),
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={},
                        rule=["echo", "hello", "again"],
                    ),
                ]
            ),
        ),
        # Rule as a list of strings
        (
            cimple.models.pkg_config.PkgConfigRulesSection(
                default=[
                    "echo hello",
                    cimple.models.pkg_config.PkgConfigRule.model_construct(
                        rule=["echo", "hello again"]
                    ),
                ]
            ),
            pathlib.Path("/default"),
            {},
            [],
            cimple.models.pkg_config.PkgConfigNormalizedRulesList.model_construct(
                [
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={},
                        rule=["echo", "hello"],
                    ),
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={},
                        rule=["echo", "hello again"],
                    ),
                ]
            ),
        ),
        # Rule with different cwd
        (
            cimple.models.pkg_config.PkgConfigRulesSection(
                default=[
                    "echo hello",
                    cimple.models.pkg_config.PkgConfigRule.model_construct(
                        cwd="some/path", rule="echo hello again"
                    ),
                ]
            ),
            pathlib.Path("/default"),
            {},
            [],
            cimple.models.pkg_config.PkgConfigNormalizedRulesList.model_construct(
                [
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={},
                        rule=["echo", "hello"],
                    ),
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default/some/path"),
                        env={},
                        rule=["echo", "hello", "again"],
                    ),
                ]
            ),
        ),
        # Rule with extra paths
        (
            cimple.models.pkg_config.PkgConfigRulesSection(
                default=[
                    "echo hello",
                    cimple.models.pkg_config.PkgConfigRule.model_construct(rule="echo hello again"),
                ]
            ),
            pathlib.Path("/default"),
            {},
            [pathlib.Path("/some/extra/path"), pathlib.Path("/another/extra/path")],
            cimple.models.pkg_config.PkgConfigNormalizedRulesList.model_construct(
                [
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={"PATH": os.pathsep.join(["/some/extra/path", "/another/extra/path"])},
                        rule=["echo", "hello"],
                    ),
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={"PATH": os.pathsep.join(["/some/extra/path", "/another/extra/path"])},
                        rule=["echo", "hello", "again"],
                    ),
                ]
            ),
        ),
        # Rule with envs
        (
            cimple.models.pkg_config.PkgConfigRulesSection(
                default=[
                    "echo hello",
                    cimple.models.pkg_config.PkgConfigRule.model_construct(
                        rule="echo hello again", env={"PATH": "/abc", "DEF": "def"}
                    ),
                ]
            ),
            pathlib.Path("/default"),
            {},
            [pathlib.Path("/some/extra/path"), pathlib.Path("/another/extra/path")],
            cimple.models.pkg_config.PkgConfigNormalizedRulesList.model_construct(
                [
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={"PATH": os.pathsep.join(["/some/extra/path", "/another/extra/path"])},
                        rule=["echo", "hello"],
                    ),
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={
                            "PATH": os.pathsep.join(
                                ["/abc", "/some/extra/path", "/another/extra/path"]
                            ),
                            "DEF": "def",
                        },
                        rule=["echo", "hello", "again"],
                    ),
                ]
            ),
        ),
        # Rule with variable interpolation
        (
            cimple.models.pkg_config.PkgConfigRulesSection(
                default=[
                    "echo ${var}",
                    cimple.models.pkg_config.PkgConfigRule.model_construct(
                        rule="echo hello ${var}", env={"PATH": "/abc", "DEF": "${var}"}
                    ),
                ]
            ),
            pathlib.Path("/default"),
            {"var": "value with space"},
            [pathlib.Path("/some/extra/path"), pathlib.Path("/another/extra/path")],
            cimple.models.pkg_config.PkgConfigNormalizedRulesList.model_construct(
                [
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={"PATH": os.pathsep.join(["/some/extra/path", "/another/extra/path"])},
                        rule=["echo", "value with space"],
                    ),
                    cimple.models.pkg_config.PkgConfigNormalizedRule(
                        cwd=pathlib.Path("/default"),
                        env={
                            "PATH": os.pathsep.join(
                                ["/abc", "/some/extra/path", "/another/extra/path"]
                            ),
                            "DEF": "value with space",
                        },
                        rule=["echo", "hello", "value with space"],
                    ),
                ]
            ),
        ),
    ],
)
def test_normalize_rules(
    rules: cimple.models.pkg_config.PkgConfigRulesSection,
    default_cwd: pathlib.Path,
    builtin_variables: dict[str, str],
    bin_paths: list[pathlib.Path],
    expected_rules: cimple.models.pkg_config.PkgConfigNormalizedRulesList,
):
    # GIVEN: a PkgConfigRulesSection
    # WHEN: normalizing the rules
    actual_rules = cimple.models.pkg_config.normalize_rules(
        rules,
        default_cwd=default_cwd,
        builtin_variables=builtin_variables,
        bin_paths=bin_paths,
    )

    # THEN: the rules are normalized correctly
    assert actual_rules == expected_rules
