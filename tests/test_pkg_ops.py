import pathlib
import typing
import unittest.mock

import pytest

import cimple.system
from cimple.models import pkg as pkg_models
from cimple.pkg import ops as pkg_ops
from cimple.snapshot import core as snapshot_core

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

    import tests.conftest


@pytest.mark.usefixtures("basic_cimple_store")
def test_build_pkg_custom_with_cimple_pi(cimple_pi: pathlib.Path, mocker: MockerFixture):
    # GIVEN: a real source package to build
    package_id = pkg_models.src_pkg_id("custom")
    package_version = "0.0.1-1"
    cimple_snapshot = unittest.mock.Mock()
    return_process = unittest.mock.Mock()
    return_process.returncode = 0
    run_command_mock = mocker.patch(
        "cimple.pkg.ops.cimple.process.run_command", return_value=return_process
    )
    uut = pkg_ops.PkgOps()

    # WHEN: building a custom package
    result = uut.build_pkg(
        package_id,
        package_version,
        pi_path=cimple_pi,
        cimple_snapshot=cimple_snapshot,
        build_options=pkg_ops.PackageBuildOptions(
            parallel=2, extra_paths=[pathlib.Path("/extra/path")]
        ),
    )

    # THEN: the expected build commands are called
    run_command_mock.assert_called_once()
    assert run_command_mock.call_args[0][0] == ["abc", "abc"]
    assert run_command_mock.call_args[1]["extra_paths"] == [pathlib.Path("/extra/path")]
    assert result.is_dir()


@pytest.mark.usefixtures("basic_cimple_store")
@pytest.mark.skipif(
    not cimple.system.platform_name().startswith("windows"),
    reason="Cygwin is only relevant on Windows",
)
def test_build_cygwin_pkg(
    cimple_pi: pathlib.Path,
    cygwin_release_content_side_effect: typing.Callable[
        [str], tests.conftest.MockHttpResponse | tests.conftest.MockHttp404Response
    ],
    mocker: MockerFixture,
):
    # GIVEN: A basic Cimple store with root snapshot
    _ = mocker.patch(
        "cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect
    )
    cimple_snapshot = snapshot_core.load_snapshot("root")
    uut = pkg_ops.PkgOps()

    # WHEN: Building a Cygwin package (make)
    output_path = uut.build_pkg(
        pkg_models.src_pkg_id("make"),
        "4.4.1-2",
        pi_path=cimple_pi,
        cimple_snapshot=cimple_snapshot,
        build_options=pkg_ops.PackageBuildOptions(parallel=2),
    )

    # THEN:
    assert output_path.exists(), f"Output path does not exist: {output_path}"
    assert (output_path / "usr" / "bin" / "make.exe").exists(), "make.exe not found in output"
    assert output_path.name == "make-4.4.1-2"
