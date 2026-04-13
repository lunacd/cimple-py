import os
import pathlib  # noqa: TC003
import shutil
import subprocess

import typer

import cimple.env
import cimple.logging
import cimple.models.pkg_config
import cimple.system

run_rules_app = typer.Typer()


@run_rules_app.command()
def run(rules_path: pathlib.Path):
    """
    Run rules from a rules file.

    This is used to execute a build _within_ a build sandbox. Almost all other parts of cimple runs
    outside the sandbox.
    """

    rules = cimple.models.pkg_config.PkgConfigNormalizedRulesList.model_validate_json(
        rules_path.read_text()
    )
    for rule in rules.root:
        if len(rule.rule) == 0:
            continue

        final_env = cimple.env.merge_env(os.environ, rule.env)
        full_cmd = shutil.which(rule.rule[0], path=final_env["PATH"])
        if full_cmd is None:
            raise RuntimeError(f"Could not find {rule.rule[0]}")
        rule.rule[0] = full_cmd
        cimple.logging.debug("Running %s in %s with %s.", rule.rule, rule.cwd, final_env)
        result_process = subprocess.run(rule.rule, env=final_env, cwd=rule.cwd)
        if result_process.returncode != 0:
            raise RuntimeError(
                f"Rule {rule.rule} failed with exit code {result_process.returncode}"
            )
