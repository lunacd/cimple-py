import copy
import importlib.resources
import typing

import pytest

import cimple.constants
import cimple.models.pkg
import cimple.models.snapshot
import cimple.pkg.ops
import cimple.snapshot.core
import cimple.snapshot.ops
import cimple.util

if typing.TYPE_CHECKING:
    import pathlib

    import pyfakefs.fake_filesystem
    from pytest_mock import MockerFixture

    import tests.conftest


class TestSnapshotCore:
    def test_add_pkg_to_snapshot(self, helpers: tests.conftest.Helpers):
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

    @pytest.mark.usefixtures("fs")
    def test_snapshot_dump(self, helpers: tests.conftest.Helpers):
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


class TestSnapshotOps:
    @pytest.mark.usefixtures("basic_cimple_store")
    def test_snapshot_add_unresolvable_binary_dep(
        self,
        cimple_pi: pathlib.Path,
        cygwin_release_content_side_effect: typing.Callable[
            [str], tests.conftest.MockHttpResponse | tests.conftest.MockHttp404Response
        ],
        mocker: MockerFixture,
        helpers: tests.conftest.Helpers,
    ):
        # GIVEN: a root snapshot
        _ = mocker.patch(
            "cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect
        )
        root_snapshot = helpers.mock_cimple_snapshot([])

        # WHEN: adding a package to the snapshot
        # THEN: an exception is raised because cygwin is not in the snapshot
        with pytest.raises(
            RuntimeError,
            match="Binary dependency cygwin for package make not found in snapshot",
        ):
            _ = cimple.snapshot.ops.add(
                root_snapshot,
                [
                    cimple.snapshot.ops.VersionedSourcePackage(
                        id=cimple.models.pkg.SrcPkgId("make"), version="4.4.1-2"
                    )
                ],
                cimple_pi,
                parallel=1,
            )

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_snapshot_add_unresolvable_build_dep(
        self,
        cimple_pi: pathlib.Path,
        cygwin_release_content_side_effect: typing.Callable[
            [str], tests.conftest.MockHttpResponse | tests.conftest.MockHttp404Response
        ],
        mocker: MockerFixture,
        helpers: tests.conftest.Helpers,
    ):
        # GIVEN: a root snapshot
        _ = mocker.patch(
            "cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect
        )
        root_snapshot = helpers.mock_cimple_snapshot([cimple.models.pkg.BinPkgId("pkg2-bin")])

        # WHEN: adding a package to the snapshot
        # THEN: an exception is raised because cygwin is not in the snapshot
        with pytest.raises(
            RuntimeError,
            match="Build dependency pkg1-bin for package custom not found in snapshot",
        ):
            _ = cimple.snapshot.ops.add(
                root_snapshot,
                [
                    cimple.snapshot.ops.VersionedSourcePackage(
                        id=cimple.models.pkg.SrcPkgId("custom"), version="0.0.1-1"
                    )
                ],
                cimple_pi,
                parallel=1,
            )

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_snapshot_add_simple(
        self,
        cimple_pi: pathlib.Path,
        cygwin_release_content_side_effect: typing.Callable[
            [str], tests.conftest.MockHttpResponse | tests.conftest.MockHttp404Response
        ],
        mocker: MockerFixture,
        helpers: tests.conftest.Helpers,
    ):
        # GIVEN: a snapshot with make's binary dependencies
        _ = mocker.patch(
            "cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect
        )
        snapshot = helpers.mock_cimple_snapshot(
            [
                cimple.models.pkg.BinPkgId("cygwin"),
                cimple.models.pkg.BinPkgId("libguile3.0_1"),
                cimple.models.pkg.BinPkgId("libintl8"),
            ]
        )

        # WHEN: adding a package to the snapshot
        new_snapshot = cimple.snapshot.ops.add(
            snapshot,
            [
                cimple.snapshot.ops.VersionedSourcePackage(
                    id=cimple.models.pkg.SrcPkgId("make"), version="4.4.1-2"
                )
            ],
            cimple_pi,
            parallel=1,
        )

        # THEN: the package should be in the snapshot
        assert cimple.models.pkg.SrcPkgId("make") in new_snapshot.src_pkg_map
        assert cimple.models.pkg.BinPkgId("make") in new_snapshot.bin_pkg_map

        # THEN: pkg exists in the pkg store
        make_bin_pkg = new_snapshot.bin_pkg_map[cimple.models.pkg.BinPkgId("make")]
        sha256 = make_bin_pkg.sha256
        assert (cimple.constants.cimple_pkg_dir / f"make-{sha256}.tar.xz").exists()

        # THEN: the dependencies are correct
        assert all(d.type == "bin" for d in make_bin_pkg.depends)
        assert sorted([d.name for d in make_bin_pkg.depends]) == [
            "cygwin",
            "libguile3.0_1",
            "libintl8",
        ]

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_snapshot_add_multiple_packages(
        self,
        cimple_pi: pathlib.Path,
        cygwin_release_content_side_effect: typing.Callable[
            [str], tests.conftest.MockHttpResponse | tests.conftest.MockHttp404Response
        ],
        mocker: MockerFixture,
        helpers: tests.conftest.Helpers,
    ):
        # GIVEN: a snapshot with make's binary dependencies, except cygwin
        _ = mocker.patch(
            "cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect
        )
        snapshot = helpers.mock_cimple_snapshot(
            [
                cimple.models.pkg.BinPkgId("libguile3.0_1"),
                cimple.models.pkg.BinPkgId("cygwin"),
                cimple.models.pkg.BinPkgId("libiconv2"),
            ]
        )

        # WHEN: adding both make and cygwin to the snapshot
        # Note that cygwin is specified after make, in the reverse order of their dependency
        # relationship. This is to verify that the order of packages specified does not matter.
        new_snapshot = cimple.snapshot.ops.add(
            snapshot,
            [
                cimple.snapshot.ops.VersionedSourcePackage(
                    id=cimple.models.pkg.SrcPkgId("make"), version="4.4.1-2"
                ),
                cimple.snapshot.ops.VersionedSourcePackage(
                    id=cimple.models.pkg.SrcPkgId("libintl8"), version="0.22.5-1"
                ),
            ],
            cimple_pi,
            parallel=1,
        )

        # THEN: the package should be in the snapshot
        assert cimple.models.pkg.SrcPkgId("make") in new_snapshot.src_pkg_map
        assert cimple.models.pkg.BinPkgId("make") in new_snapshot.bin_pkg_map

        # THEN: pkg exists in the pkg store
        make_bin_pkg = new_snapshot.bin_pkg_map[cimple.models.pkg.BinPkgId("make")]
        sha256 = make_bin_pkg.sha256
        assert (cimple.constants.cimple_pkg_dir / f"make-{sha256}.tar.xz").exists()

        # THEN: the dependencies are correct
        assert all(d.type == "bin" for d in make_bin_pkg.depends)
        assert sorted([d.name for d in make_bin_pkg.depends]) == [
            "cygwin",
            "libguile3.0_1",
            "libintl8",
        ]

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_snapshot_add_custom(
        self,
        cimple_pi: pathlib.Path,
        mocker: MockerFixture,
        fs: pyfakefs.fake_filesystem.FakeFilesystem,
    ):
        # GIVEN: a snapshot with make's binary dependencies
        snapshot = cimple.snapshot.core.load_snapshot("test-snapshot")
        with importlib.resources.path("tests", "data", "dummy_output") as dummy_output_path:
            fs.makedirs(dummy_output_path.as_posix())
            fs.create_file(dummy_output_path / "custom.txt")
            mocker.patch(
                "cimple.pkg.ops.PkgOps._build_custom_pkg",
                return_value={"custom": dummy_output_path},
            )

        # WHEN: adding a package to the snapshot
        new_snapshot = cimple.snapshot.ops.add(
            snapshot,
            [
                cimple.snapshot.ops.VersionedSourcePackage(
                    id=cimple.models.pkg.SrcPkgId("custom"), version="0.0.1-1"
                )
            ],
            cimple_pi,
            parallel=1,
        )

        # THEN: the package should be in the snapshot
        assert cimple.models.pkg.SrcPkgId("custom") in new_snapshot.src_pkg_map
        assert cimple.models.pkg.BinPkgId("custom") in new_snapshot.bin_pkg_map

        # THEN: pkg exists in the pkg store
        make_bin_pkg = new_snapshot.bin_pkg_map[cimple.models.pkg.BinPkgId("custom")]
        sha256 = make_bin_pkg.sha256
        assert (cimple.constants.cimple_pkg_dir / f"custom-{sha256}.tar.xz").exists()

        # THEN: the dependencies are correct
        assert all(d.type == "bin" for d in make_bin_pkg.depends)
        assert sorted([d.name for d in make_bin_pkg.depends]) == [
            "pkg2-bin",
        ]


class TestComputeBuildGraph:
    @pytest.mark.usefixtures("basic_cimple_store")
    def test_compute_build_graph_empty(self):
        # GIVEN: a snapshot and no changes
        snapshot = cimple.snapshot.core.load_snapshot("test-snapshot")
        changes = cimple.models.snapshot.SnapshotChanges.model_construct(
            add=[], remove=[], update=[]
        )

        # WHEN: computing the build graph
        build_graph = cimple.snapshot.ops.compute_build_graph(snapshot, changes)

        # THEN: the build graph is empty
        assert build_graph.graph.number_of_nodes() == 0

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_compute_build_graph(self):
        # GIVEN: a snapshot and changes
        snapshot = cimple.snapshot.core.load_snapshot("test-snapshot")
        pkg_to_add = cimple.models.snapshot.SnapshotChangeAdd(name="pkg1", version="1.0")
        pkg_to_update = cimple.models.snapshot.SnapshotChangeUpdate.model_construct(
            name="pkg4", from_version="0.1", to_version="1.0"
        )
        changes = cimple.models.snapshot.SnapshotChanges.model_construct(
            add=[pkg_to_add], remove=[cimple.models.pkg.SrcPkgId("pkg5")], update=[pkg_to_update]
        )

        # WHEN: computing the build graph
        build_graph = cimple.snapshot.ops.compute_build_graph(snapshot, changes)

        # THEN: the build graph contains the new package
        assert build_graph.graph.number_of_nodes() == 6

        # THEN: the graph has exactly the expected edges
        expected_edges = {
            (cimple.models.pkg.SrcPkgId("pkg1"), cimple.models.pkg.BinPkgId("pkg1-bin")),
            (cimple.models.pkg.BinPkgId("pkg2-bin"), cimple.models.pkg.SrcPkgId("pkg1")),
            (cimple.models.pkg.SrcPkgId("pkg2"), cimple.models.pkg.BinPkgId("pkg2-bin")),
            (cimple.models.pkg.SrcPkgId("pkg4"), cimple.models.pkg.BinPkgId("pkg4-bin")),
            (cimple.models.pkg.BinPkgId("pkg4-bin"), cimple.models.pkg.SrcPkgId("pkg2")),
        }
        actual_edges = set(build_graph.graph.edges())
        assert actual_edges == expected_edges
