import json
import pathlib
import tempfile
import typing

import pytest

import cimple.cmd.run_rules

if typing.TYPE_CHECKING:
    import pytest_mock


@pytest.mark.usefixtures("fs")
def test_run_rules_cmd(mocker: pytest_mock.MockerFixture):
    # GIVEN: a rules file
    rules = [{"cwd": "some dir", "rule": ["some command", "with spaces"], "env": {"foo": "bar"}}]
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = pathlib.Path(tmpdir) / "rules.json"
        rules_path.write_text(json.dumps(rules))

        process_mock = mocker.Mock()
        process_mock.returncode = 0
        subprocess_run_mock = mocker.patch(
            "cimple.cmd.run_rules.subprocess.run", return_value=process_mock
        )
        mocker.patch("cimple.cmd.run_rules.shutil.which", return_value="/path/to/cmd")

        # WHEN: run_rules_cmd is invoked on the rules file
        cimple.cmd.run_rules.run(rules_path)

        # THEN: the expected subprocess calls are invoked
        subprocess_run_mock.assert_called_once()
        assert subprocess_run_mock.call_args[0][0] == ["/path/to/cmd", "with spaces"]
        assert str(subprocess_run_mock.call_args.kwargs["cwd"]) == "some dir"
        actual_env = subprocess_run_mock.call_args.kwargs["env"]
        assert rules[0]["env"].items() <= actual_env.items()


@pytest.mark.usefixtures("fs")
def test_run_rules_cmd_failed_cmd(mocker: pytest_mock.MockerFixture):
    # GIVEN: a rules file
    rules = [{"cwd": "some dir", "rule": ["some command", "with spaces"], "env": {"foo": "bar"}}]
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = pathlib.Path(tmpdir) / "rules.json"
        rules_path.write_text(json.dumps(rules))

        # GIVEN: a command returned non-zero
        process_mock = mocker.Mock()
        process_mock.returncode = 1
        mocker.patch("cimple.cmd.run_rules.subprocess.run", return_value=process_mock)
        mocker.patch("cimple.cmd.run_rules.shutil.which", return_value="/path/to/cmd")

        # WHEN: run_rules_cmd is invoked on the rules file
        # THEN: a RuntimeError is raised
        with pytest.raises(RuntimeError, match="failed with exit code 1"):
            cimple.cmd.run_rules.run(rules_path)


@pytest.mark.usefixtures("fs")
def test_run_rules_cmd_not_found(mocker: pytest_mock.MockerFixture):
    # GIVEN: a rules file
    rules = [{"cwd": "some dir", "rule": ["some command", "with spaces"], "env": {"foo": "bar"}}]
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = pathlib.Path(tmpdir) / "rules.json"
        rules_path.write_text(json.dumps(rules))

        # GIVEN: a command returned non-zero
        mocker.patch("cimple.cmd.run_rules.shutil.which", return_value=None)

        # WHEN: run_rules_cmd is invoked on the rules file
        # THEN: a RuntimeError is raised
        with pytest.raises(RuntimeError, match="Could not find some command"):
            cimple.cmd.run_rules.run(rules_path)
