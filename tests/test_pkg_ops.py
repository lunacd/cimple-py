from unittest import mock

import pytest

from cimple import common
from cimple.models import pkg as pkg_models
from cimple.pkg import ops as pkg_ops
from cimple.snapshot import core as snapshot_core


def test_build_pkg_custom_with_cimple_pi(cimple_pi, basic_cimple_store, mocker):
    # GIVEN: a real source package to build
    package_id = pkg_models.src_pkg_id("custom")
    package_version = "0.0.1-1"
    cimple_snapshot = mock.Mock()
    return_process = mock.Mock()
    return_process.returncode = 0
    run_command_mock = mocker.patch(
        "cimple.pkg.ops.common.cmd.run_command", return_value=return_process
    )

    # WHEN: building a custom package
    result = pkg_ops.build_pkg(
        package_id,
        package_version,
        pi_path=cimple_pi,
        cimple_snapshot=cimple_snapshot,
        parallel=2,
    )

    # THEN: the expected build commands are called
    run_command_mock.assert_called_once()
    assert run_command_mock.call_args[0][0] == ["abc", "abc"]
    assert result.is_dir()


@pytest.mark.skipif(
    not common.system.platform_name().startswith("windows"),
    reason="Cygwin is only relevant on Windows",
)
def test_build_cygwin_pkg(
    basic_cimple_store, cimple_pi, cygwin_release_content_side_effect, mocker
):
    # GIVEN: A basic Cimple store with root snapshot
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect)
    cimple_snapshot = snapshot_core.load_snapshot("root")

    # WHEN: Building a Cygwin package (make)
    output_path = pkg_ops.build_pkg(
        pkg_models.src_pkg_id("make"),
        "4.4.1-2",
        pi_path=cimple_pi,
        cimple_snapshot=cimple_snapshot,
        parallel=8,
    )

    # THEN:
    assert output_path.exists(), f"Output path does not exist: {output_path}"
    assert (output_path / "usr" / "bin" / "make.exe").exists(), "make.exe not found in output"
    assert output_path.name == "make-4.4.1-2"
