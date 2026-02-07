import pathlib
import typing
import unittest.mock

import pytest

import cimple.models
import cimple.models.pkg
import cimple.system
from cimple.models import pkg as pkg_models
from cimple.pkg import ops as pkg_ops
from cimple.snapshot import core as snapshot_core

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

    import tests.conftest


class TestPkgOps:
    @pytest.mark.usefixtures("basic_cimple_store")
    def test_build_pkg_custom_with_cimple_pi(self, cimple_pi: pathlib.Path, mocker: MockerFixture):
        # GIVEN: a real source package to build
        package_id = pkg_models.SrcPkgId("custom")
        cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")
        cimple_snapshot.add_src_pkg(package_id, "0.0.1-1", [])
        return_process = unittest.mock.Mock()
        return_process.returncode = 0
        run_command_mock = mocker.patch(
            "cimple.pkg.ops.cimple.process.run_command", return_value=return_process
        )
        uut = pkg_ops.PkgOps()

        # WHEN: building a custom package
        result = uut.build_pkg(
            package_id,
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
        assert len(result) == 1
        assert "custom" in result
        assert result["custom"].is_dir()

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_build_pkg_custom_with_multiple_binaries(
        self, cimple_pi: pathlib.Path, mocker: MockerFixture
    ):
        # GIVEN: a real source package to build
        package_id = pkg_models.SrcPkgId("multiple_binaries")
        cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")
        cimple_snapshot.add_src_pkg(package_id, "0.0.1-1", [])
        return_process = unittest.mock.Mock()
        return_process.returncode = 0
        run_command_mock = mocker.patch(
            "cimple.pkg.ops.cimple.process.run_command", return_value=return_process
        )
        uut = pkg_ops.PkgOps()

        # WHEN: building a custom package
        result = uut.build_pkg(
            package_id,
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
        assert len(result) == 2
        assert "multiple1" in result
        assert result["multiple1"].is_dir()
        assert "multiple2" in result
        assert result["multiple2"].is_dir()

    @pytest.mark.usefixtures("basic_cimple_store")
    @pytest.mark.skipif(
        not cimple.system.platform_name().startswith("windows"),
        reason="Cygwin is only relevant on Windows",
    )
    def test_build_cygwin_pkg(
        self,
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
        cimple_snapshot.add_src_pkg(pkg_models.SrcPkgId("make"), "4.4.1-2", [])
        uut = pkg_ops.PkgOps()

        # WHEN: Building a Cygwin package (make)
        output_paths = uut.build_pkg(
            pkg_models.SrcPkgId("make"),
            pi_path=cimple_pi,
            cimple_snapshot=cimple_snapshot,
            build_options=pkg_ops.PackageBuildOptions(parallel=2),
        )

        # THEN:
        assert len(output_paths) == 1
        assert "make" in output_paths
        assert output_paths["make"].exists(), f"Output path does not exist: {output_paths}"
        assert (output_paths["make"] / "usr" / "bin" / "make.exe").exists(), (
            "make.exe not found in output"
        )
        assert output_paths["make"].name == "make-4.4.1-2"


class TestResolveDeps:
    def test_resolve_bootstrap_deps(self, cimple_pi: pathlib.Path):
        # GIVEN: a package processor
        uut = pkg_ops.PkgOps()

        # WHEN: resolving bootstrap1 v1.0.0-1 dependencies
        result = uut.resolve_dependencies(
            cimple.models.pkg.SrcPkgId("bootstrap1"),
            "1.0.0-1",
            pi_path=cimple_pi,
            is_bootstrap=True,
        )

        # THEN: the expected dependencies are returned
        assert result.build_depends == {
            cimple.models.pkg.SrcPkgId("bootstrap1"): [
                cimple.models.pkg.BinPkgId("bootstrap:bootstrap1-bin")
            ],
            cimple.models.pkg.SrcPkgId("bootstrap:bootstrap1"): [
                cimple.models.pkg.BinPkgId("prev:bootstrap1-bin")
            ],
        }
        assert result.depends == {
            cimple.models.pkg.BinPkgId("bootstrap1-bin"): [],
            cimple.models.pkg.BinPkgId("bootstrap:bootstrap1-bin"): [],
        }
