import importlib.resources
import json
import pathlib

import pyfakefs.fake_filesystem
import pytest

from cimple import common


@pytest.fixture(name="basic_cimple_store")
def basic_cimple_store_fixture(fs: pyfakefs.fake_filesystem.FakeFilesystem) -> None:
    # Create snapshot
    snapshot_data = {
        "version": 0,
        "name": "test_snapshot",
        "pkgs": [
            {
                "name": "pkg1",
                "version": "1.0",
                "pkg_type": "src",
                "build_depends": ["pkg2-bin"],
                "binary_packages": ["pkg1-bin"],
            },
            {
                "name": "pkg1-bin",
                "sha256": "a4defb8341593d4deea245993aeb3ce54de060affb10cb9ae60ec3789dd3f241",
                "pkg_type": "bin",
                "compression_method": "xz",
                "depends": [],
            },
            {
                "name": "pkg2",
                "version": "1.0",
                "pkg_type": "src",
                "build_depends": [],
                "binary_packages": ["pkg2-bin"],
            },
            {
                "name": "pkg2-bin",
                "sha256": "ba3a73d0ce858c0da55186acb6b30de036a283812b55e48966f43b5704611914",
                "pkg_type": "bin",
                "compression_method": "xz",
                "depends": ["pkg3-bin"],
            },
            {
                "name": "pkg3",
                "version": "1.0",
                "pkg_type": "src",
                "build_depends": [],
                "binary_packages": ["pkg3-bin"],
            },
            {
                "name": "pkg3-bin",
                "sha256": "870f2deea4a3981df6ed4cccd05df2bd3465a7556e952e812df0cf46240008ec",
                "pkg_type": "bin",
                "compression_method": "xz",
                "depends": [],
            },
        ],
        "ancestor": "root",
        "changes": {"add": [], "remove": []},
    }
    fs.create_file(
        common.constants.cimple_snapshot_dir / "test-snapshot.json",
        contents=json.dumps(snapshot_data),
    )

    # Add binary packages
    for pkg in snapshot_data["pkgs"]:
        if pkg["pkg_type"] != "bin":
            continue

        pkg_tarball_name = f"{pkg['name']}-{pkg['sha256']}.tar.{pkg['compression_method']}"
        with importlib.resources.path("tests", f"data/pkg/{pkg_tarball_name}") as pkg_path:
            fs.add_real_file(
                pkg_path,
                read_only=False,
                target_path=common.constants.cimple_pkg_dir / pkg_tarball_name,
            )


@pytest.fixture(name="cimple_pi")
def cimple_pi_fixture(fs: pyfakefs.fake_filesystem.FakeFilesystem) -> pathlib.Path:
    pi_target_path = pathlib.Path("/pi")
    with importlib.resources.path("tests", "data/pi") as pi_path:
        fs.add_real_directory(pi_path, target_path=pi_target_path, read_only=True)
    return pi_target_path
