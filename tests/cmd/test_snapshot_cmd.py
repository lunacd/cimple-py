import pathlib

from cimple.cmd import snapshot as snapshot_cmd
from cimple.models import pkg as pkg_models
from cimple.models import snapshot as snapshot_models
from cimple.snapshot import core as snapshot_core
from cimple.snapshot import ops as snapshot_ops

root_snapshot_data = snapshot_models.SnapshotModel(
    version=0,
    name="root",
    pkgs=[],
    ancestor=None,
    changes=snapshot_models.SnapshotChanges(add=[], remove=[], update=[]),
)

dummy_snapshot_data = snapshot_models.SnapshotModel.model_validate(
    {
        "version": 0,
        "name": "dummy",
        "pkgs": [
            {
                "name": "pkg1",
                "version": "1.0",
                "pkg_type": "src",
                "build_depends": [],
                "binary_packages": ["pkg1"],
            },
            {
                "name": "pkg1",
                "pkg_type": "bin",
                "sha256": "dummy_sha256_bin_pkg1",
                "depends": [],
                "compression_method": "xz",
            },
        ],
        "ancestor": "root",
        "changes": {"add": [], "remove": [], "update": []},
    }
)


def load_snapshot_side_effect(snapshot_name: str) -> snapshot_core.CimpleSnapshot:
    match snapshot_name:
        case "root":
            return snapshot_core.CimpleSnapshot(root_snapshot_data)
        case "dummy":
            return snapshot_core.CimpleSnapshot(dummy_snapshot_data)
    raise NotImplementedError


def test_snapshot_change(mocker):
    # GIVEN: a dummy snapshot
    snapshot_name = "dummy"
    pkg_index_path = pathlib.Path("/path/to/pkg/index")
    load_snapshot_mock = mocker.patch(
        "cimple.cmd.snapshot.snapshot_core.load_snapshot",
        side_effect=load_snapshot_side_effect,
    )
    add_mock = mocker.patch("cimple.cmd.snapshot.snapshot_ops.add")
    dummy_snapshot_value = load_snapshot_side_effect(snapshot_name)

    # WHEN: a change command is invoked on it
    snapshot_cmd.change(
        snapshot_name, add=["pkg1=1.0", "pkg2=2.0"], pkg_index=pkg_index_path.as_posix(), parallel=2
    )

    # THEN: add is called for pkg1 and pkg2 on the loaded snapshot
    load_snapshot_mock.assert_called_once_with(snapshot_name)
    add_mock.assert_called_once_with(
        origin_snapshot=dummy_snapshot_value,
        packages=[
            snapshot_ops.VersionedSourcePackage(id=pkg_models.SrcPkgId("pkg1"), version="1.0"),
            snapshot_ops.VersionedSourcePackage(id=pkg_models.SrcPkgId("pkg2"), version="2.0"),
        ],
        pkg_index_path=pkg_index_path,
        parallel=2,
        extra_paths=[],
    )


def test_snapshot_reproduce(mocker):
    # GIVEN: a dummy snapshot
    snapshot_name = "dummy"
    pkg_index_path = pathlib.Path("/path/to/pkg/index")
    load_snapshot_mock = mocker.patch(
        "cimple.cmd.snapshot.snapshot_core.load_snapshot",
        side_effect=load_snapshot_side_effect,
    )
    result_snapshot_mock = load_snapshot_side_effect("dummy")
    compare_mock = mocker.patch.object(result_snapshot_mock, "compare_pkgs_with", return_value=None)
    add_mock = mocker.patch(
        "cimple.cmd.snapshot.snapshot_ops.add", return_value=result_snapshot_mock
    )
    root_snapshot_value = load_snapshot_side_effect("root")
    dummy_snapshot_value = load_snapshot_side_effect("dummy")

    # WHEN: a reproduce command is invoked on it
    snapshot_cmd.reproduce(
        snapshot_name,
        pkg_index=pkg_index_path.as_posix(),
        parallel=1,
    )

    # THEN: load is called on both target snapshot and root
    load_snapshot_mock.assert_any_call(snapshot_name)
    load_snapshot_mock.assert_any_call("root")

    # THEN: add is called to reproduce the target snapshot
    add_mock.assert_called_once_with(
        root_snapshot_value,
        [snapshot_ops.VersionedSourcePackage(id=pkg_models.SrcPkgId("pkg1"), version="1.0")],
        pkg_index_path=pkg_index_path,
        parallel=1,
    )

    # THEN: compare is called on two snapshots
    compare_mock.assert_called_once_with(
        dummy_snapshot_value,
    )
