import pathlib

import pytest

import cimple.snapshot.core as snapshot_core
from cimple.models import pkg as pkg_models
from cimple.pkg import ops as pkg_ops


@pytest.mark.usefixtures("basic_cimple_store")
def test_install_single_pkg():
    # Given: a basic snapshot with binary packages
    cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")
    pkg1 = pkg_models.BinPkgId("pkg1-bin")
    uut = pkg_ops.PkgOps()

    # When: installing a single package
    uut.install_pkg(pathlib.Path("/target/"), pkg1, cimple_snapshot)

    # Then: the installation result is successful and includes the expected binary packages
    expected_file = pathlib.Path("/target/pkg-1.txt")
    assert expected_file.exists(), f"Expected file {expected_file} should exist after installation"
    assert expected_file.read_text().strip() == ""


@pytest.mark.usefixtures("basic_cimple_store")
def test_install_pkg_with_dependencies():
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
