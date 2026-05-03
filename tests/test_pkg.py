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


class TestPkgInstall:
    @pytest.mark.usefixtures("basic_cimple_store")
    def test_install_single_pkg(self):
        # Given: a basic snapshot with binary packages
        cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")
        pkg1 = pkg_models.BinPkgId("pkg1-bin")
        uut = pkg_ops.PkgOps()

        # When: installing a single package
        uut.install_pkg(pathlib.Path("/target/"), pkg1, cimple_snapshot)

        # Then: the installation result is successful and includes the expected binary packages
        expected_file = pathlib.Path("/target/pkg-1.txt")
        assert expected_file.exists(), (
            f"Expected file {expected_file} should exist after installation"
        )
        assert expected_file.read_text().strip() == ""

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_install_pkg_with_dependencies(self):
        # Given: a basic snapshot with binary packages
        cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")
        pkg2 = pkg_models.BinPkgId("pkg2-bin")
        uut = pkg_ops.PkgOps()

        # When: installing a package with dependencies
        uut.install_package_and_deps(pathlib.Path("/target/"), pkg2, cimple_snapshot)

        # Then: the installation result is successful and includes the expected binary packages
        #       pkg2-bin depends on pkg3-bin, so both should be installed
        expected_files = [
            pathlib.Path("/target/pkg-2.txt"),
            pathlib.Path("/target/pkg-3.txt"),
        ]
        expected_content = ["hahaha", "This is package 3"]
        for expected_file, content in zip(expected_files, expected_content):
            assert expected_file.exists(), (
                f"Expected file {expected_file} should exist after installation"
            )
            assert expected_file.read_text().strip() == content

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_install_bootstrap_pkg(self):
        # Given: a basic snapshot with bootstrap packages
        cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")
        pkg1 = pkg_models.BinPkgId("bootstrap:bootstrap1-bin")
        uut = pkg_ops.PkgOps()

        # When: installing a bootstrap package
        uut.install_pkg(pathlib.Path("/target/"), pkg1, cimple_snapshot)

        # Then: the installation result is successful and includes the expected bootstrap packages
        expected_file = pathlib.Path("/target/bootstrap-bootstrap-1.txt")
        assert expected_file.exists(), (
            f"Expected file {expected_file} should exist after installation"
        )
        assert expected_file.read_text().strip() == ""

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_install_placeholder_pkg(self):
        # Given: a basic snapshot with a package's sha missing
        cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")
        pkg = pkg_models.BinPkgId("bootstrap:bootstrap1-bin")
        uut = pkg_ops.PkgOps()
        cimple_snapshot.bootstrap_bin_pkg_map[pkg].sha256 = "placeholder"

        # When: installing a placeholder package
        # Then: a RuntimeError is raised indicating that the package cannot be installed
        with pytest.raises(
            RuntimeError,
            match="Package bootstrap:bootstrap1-bin is not ready yet and cannot be installed.",
        ):
            uut.install_pkg(pathlib.Path("/target/"), pkg, cimple_snapshot)

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_install_prev_package(self, mocker: MockerFixture):
        # GIVEN: a snapshot
        cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")
        pkg = pkg_models.BinPkgId("prev:bootstrap1-bin")
        mock_tarfile_open = mocker.patch("cimple.pkg.ops.tarfile.open")

        # WHEN: installing a prev package
        uut = pkg_ops.PkgOps()
        uut.install_pkg(pathlib.Path("/target/"), pkg, cimple_snapshot)

        # THEN: the tarball with sha256 from the ancestor snapshot should be extracted
        mock_tarfile_open.assert_called_once()
        opened_path = mock_tarfile_open.call_args[0][0]
        assert "sha256-in-ancestor" in str(opened_path)


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
            build_options=pkg_ops.PackageBuildOptions(parallel=2, extra_paths=["/extra/path,bin"]),
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
            build_options=pkg_ops.PackageBuildOptions(parallel=2, extra_paths=["/extra/path,bin"]),
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
    def test_build_bootstrap_pkg(self, cimple_pi: pathlib.Path, mocker: MockerFixture):
        # GIVEN: a real source package to build
        package_id = pkg_models.SrcPkgId("bootstrap1")
        cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")
        uut = pkg_ops.PkgOps()

        # Mock the run_command function during bootstrap build
        return_process = unittest.mock.Mock()
        return_process.returncode = 0
        run_command_mock = mocker.patch(
            "cimple.pkg.ops.cimple.process.run_command", return_value=return_process
        )

        # WHEN: building a bootstrap package
        result = uut.build_pkg(
            package_id,
            pi_path=cimple_pi,
            cimple_snapshot=cimple_snapshot,
            build_options=pkg_ops.PackageBuildOptions(parallel=2),
            bootstrap=True,
        )

        # THEN: the expected output is returned
        assert len(result) == 1
        assert "bootstrap1-bin" in result
        assert result["bootstrap1-bin"].is_dir()

        # THEN: the run_command function is called
        run_command_mock.assert_called_once()
        assert run_command_mock.call_args[0][0] == ["abc", "abc"]


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
