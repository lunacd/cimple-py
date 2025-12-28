import typing

import cimple.constants
import cimple.models.pkg
import cimple.models.snapshot
import cimple.util

if typing.TYPE_CHECKING:
    import pyfakefs.fake_filesystem

    import tests.conftest


def test_add_pkg_to_snapshot(helpers: tests.conftest.Helpers):
    # GIVEN: a root snapshot
    snapshot = helpers.mock_cimple_snapshot([])

    # WHEN: adding a source package
    pkg_id = cimple.models.pkg.SrcPkgId("cmake")
    snapshot.add_src_pkg(pkg_id, "4.0.3-0", [])

    # THEN: the source package is added to the snapshot
    assert pkg_id in snapshot.src_pkg_map
    source_snapshot_pkg = snapshot.src_pkg_map[pkg_id]
    assert source_snapshot_pkg.name == "cmake"

    # WHEN: adding a binary package
    bin_pkg_id = cimple.models.pkg.BinPkgId("cmake")
    snapshot.add_bin_pkg(bin_pkg_id, pkg_id, "dummysha256", [])

    # THEN: the binary package is added to the snapshot
    assert bin_pkg_id in snapshot.bin_pkg_map
    bin_snapshot_pkg = snapshot.bin_pkg_map[bin_pkg_id]
    assert bin_snapshot_pkg.name == "cmake"
    assert source_snapshot_pkg.binary_packages == [bin_pkg_id]


def test_snapshot_dump(
    helpers: tests.conftest.Helpers, fs: pyfakefs.fake_filesystem.FakeFilesystem
):
    # GIVEN: a snapshot with a source and binary package
    cimple.util.ensure_path(cimple.constants.cimple_snapshot_dir)
    snapshot = helpers.mock_cimple_snapshot([])

    pkg_id = cimple.models.pkg.SrcPkgId("cmake")
    snapshot.add_src_pkg(pkg_id, "4.0.3-0", [])

    # WHEN: dumping the snapshot
    snapshot.dump_snapshot()

    # THEN: the snapshot file should exist
    snapshot_files = list(cimple.constants.cimple_snapshot_dir.iterdir())
    assert len(snapshot_files) == 1, f"Expected 1 snapshot file, found {len(snapshot_files)}"

    # THEN: snapshot file conforms to snapshot schema
    with snapshot_files[0].open("r") as f:
        cimple.models.snapshot.SnapshotModel.model_validate_json(f.read())
