import pathlib

from cimple import models, pkg, snapshot


def test_install_single_pkg(basic_cimple_store: None):
    # Given: a basic snapshot with binary packages
    snapshot_map = snapshot.ops.load_snapshot("test-snapshot")
    pkg1 = models.snapshot.get_snapshot_pkg_from_str_id(snapshot_map, "bin:pkg1-bin")
    assert pkg1 is not None, "Package pkg1-bin should exist in the snapshot"
    assert models.snapshot.snapshot_pkg_is_bin(pkg1.root)

    # When: installing a single package
    pkg.ops.install_pkg(pathlib.Path("/target/"), pkg1.root.id, snapshot_map)

    # Then: the installation result is successful and includes the expected binary packages
    expected_file = pathlib.Path("/target/pkg-1.txt")
    assert expected_file.exists(), f"Expected file {expected_file} should exist after installation"
    assert expected_file.read_text().strip() == ""


def test_install_pkg_with_dependencies(basic_cimple_store: None):
    # Given: a basic snapshot with binary packages
    snapshot_map = snapshot.ops.load_snapshot("test-snapshot")
    pkg2 = models.snapshot.get_snapshot_pkg_from_str_id(snapshot_map, "bin:pkg2-bin")
    assert pkg2 is not None, "Package pkg2-bin should exist in the snapshot"
    assert models.snapshot.snapshot_pkg_is_bin(pkg2.root)

    # When: installing a package with dependencies
    pkg.ops.install_package_and_deps(pathlib.Path("/target/"), pkg2.root.id, snapshot_map)

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
