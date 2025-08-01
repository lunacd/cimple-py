import json
import typing

import pyfakefs.fake_filesystem
import pytest

from cimple import common, graph, models, snapshot


@pytest.fixture(name="simple_snapshot_data")
def simple_snapshot_data_fixture() -> typing.Any:
    return {
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


def test_get_build_depends(simple_snapshot_data, fs: pyfakefs.fake_filesystem.FakeFilesystem):
    fs.create_file(
        common.constants.cimple_snapshot_dir / "test-snapshot.json",
        contents=json.dumps(simple_snapshot_data),
    )

    snapshot_map = snapshot.ops.load_snapshot("test-snapshot")
    dep_graph = graph.get_dep_graph(snapshot_map)
    build_deps = graph.get_build_depends(dep_graph, models.pkg.SrcPkgId(name="pkg1", version="1.0"))
    assert sorted(build_deps) == ["bin:pkg2-bin", "bin:pkg3-bin"]
