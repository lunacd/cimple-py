import json

import pyfakefs.fake_filesystem
import pytest

from cimple import common


@pytest.fixture(name="basic_cimple_store")
def basic_cimple_store_fixture(fs: pyfakefs.fake_filesystem.FakeFilesystem) -> None:
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
                "sha256": "abc123",
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
                "sha256": "abc123",
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
                "sha256": "def456",
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
