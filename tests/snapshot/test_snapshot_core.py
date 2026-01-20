import copy
import typing

import pytest

import cimple.constants
import cimple.models.pkg
import cimple.models.snapshot
import cimple.pkg.ops
import cimple.snapshot.core
import cimple.util

if typing.TYPE_CHECKING:
    import pathlib

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


class TestSnapshotUpdate:
    @pytest.mark.usefixtures("basic_cimple_store")
    def test_no_update(self, cimple_pi: pathlib.Path):
        # GIVEN: a snapshot
        snapshot = cimple.snapshot.core.load_snapshot("test-snapshot")
        original_snapshot = copy.deepcopy(snapshot)
        pkg_processor = cimple.pkg.ops.PkgOps()

        # WHEN: adding a package
        snapshot.update_with_changes(
            changes=cimple.models.snapshot.SnapshotChanges.model_construct(
                add=[], remove=[], update=[]
            ),
            pkg_processor=pkg_processor,
            pkg_index_path=cimple_pi,
        )

        # THEN: snapshot remains unchanged
        assert snapshot.src_pkg_map == original_snapshot.src_pkg_map
        assert snapshot.bin_pkg_map == original_snapshot.bin_pkg_map
        assert snapshot.graph.nodes == original_snapshot.graph.nodes
        assert snapshot.graph.edges == original_snapshot.graph.edges

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_remove_pkg(self, cimple_pi: pathlib.Path):
        # GIVEN: a snapshot
        snapshot = cimple.snapshot.core.load_snapshot("test-snapshot")
        pkg_processor = cimple.pkg.ops.PkgOps()

        # WHEN: removing a package
        pkg_to_remove = cimple.models.pkg.SrcPkgId("pkg2")
        snapshot.update_with_changes(
            changes=cimple.models.snapshot.SnapshotChanges.model_construct(
                add=[], remove=[pkg_to_remove], update=[]
            ),
            pkg_processor=pkg_processor,
            pkg_index_path=cimple_pi,
        )

        # THEN: the package is removed from the snapshot
        assert pkg_to_remove not in snapshot.src_pkg_map
        assert cimple.models.pkg.BinPkgId("pkg2-bin") not in snapshot.bin_pkg_map

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_add_pkg(self, cimple_pi: pathlib.Path):
        # GIVEN: a snapshot
        snapshot = cimple.snapshot.core.load_snapshot("test-snapshot")
        pkg_processor = cimple.pkg.ops.PkgOps()

        # WHEN: adding a package
        pkg_to_add = cimple.models.snapshot.SnapshotChangeAdd(name="custom", version="0.0.1-1")
        snapshot.update_with_changes(
            changes=cimple.models.snapshot.SnapshotChanges.model_construct(
                add=[pkg_to_add], remove=[], update=[]
            ),
            pkg_processor=pkg_processor,
            pkg_index_path=cimple_pi,
        )

        # THEN: the package is added to the snapshot
        assert cimple.models.pkg.SrcPkgId("custom") in snapshot.src_pkg_map
        assert cimple.models.pkg.BinPkgId("custom") in snapshot.bin_pkg_map

        # THEN: custom build depends on pkg1-bin and binary package custom depends on pkg2-bin
        assert snapshot.graph.has_edge(
            cimple.models.pkg.SrcPkgId("custom"), cimple.models.pkg.BinPkgId("pkg1-bin")
        )
        assert snapshot.graph.has_edge(
            cimple.models.pkg.BinPkgId("custom"), cimple.models.pkg.BinPkgId("pkg2-bin")
        )

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_update_pkg(self, cimple_pi: pathlib.Path):
        # GIVEN: a snapshot
        snapshot = cimple.snapshot.core.load_snapshot("test-snapshot")
        pkg_processor = cimple.pkg.ops.PkgOps()

        # WHEN: updating a package
        # This update changes depends for pkg1
        # This also changes the binary name pkg1 produces to pkg1-bin2 (from pkg1-bin)
        pkg_to_update = cimple.models.snapshot.SnapshotChangeUpdate.model_construct(
            name="pkg1", from_version="1.0", to_version="2.0-1"
        )
        snapshot.update_with_changes(
            changes=cimple.models.snapshot.SnapshotChanges.model_construct(
                add=[], remove=[], update=[pkg_to_update]
            ),
            pkg_processor=pkg_processor,
            pkg_index_path=cimple_pi,
        )

        # THEN: the package is updated in the snapshot with the correct version
        updated_pkg = snapshot.src_pkg_map[cimple.models.pkg.SrcPkgId("pkg1")]
        assert updated_pkg.version == "2.0-1"

        # THEN: the old binary package is removed and the new one is added
        assert cimple.models.pkg.BinPkgId("pkg1-bin") not in snapshot.bin_pkg_map
        assert cimple.models.pkg.BinPkgId("pkg1-bin2") in snapshot.bin_pkg_map

        # THEN: pkg1 now build-depends on pkg3-bin instead of pkg2-bin
        # pkg1-bin2 now has an added depend on pkg4-bin
        assert not snapshot.graph.has_edge(
            cimple.models.pkg.SrcPkgId("pkg1"), cimple.models.pkg.BinPkgId("pkg2-bin")
        )
        assert snapshot.graph.has_edge(
            cimple.models.pkg.SrcPkgId("pkg1"), cimple.models.pkg.BinPkgId("pkg3-bin")
        )
        assert snapshot.graph.has_edge(
            cimple.models.pkg.BinPkgId("pkg1-bin2"), cimple.models.pkg.BinPkgId("pkg4-bin")
        )
