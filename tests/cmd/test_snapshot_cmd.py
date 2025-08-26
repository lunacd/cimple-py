import pathlib

from cimple.cmd import snapshot as snapshot_cmd
from cimple.models import pkg as pkg_models
from cimple.models import snapshot as snapshot_models
from cimple.snapshot import core as snapshot_core
from cimple.snapshot import ops as snapshot_ops

dummy_snapshot_data = snapshot_models.Snapshot(
    version=0,
    name="dummy",
    pkgs=[],
    ancestor="root",
    changes=snapshot_models.SnapshotChanges(add=[], remove=[]),
)


def load_snapshot_side_effect(*args):
    return snapshot_core.CimpleSnapshot(dummy_snapshot_data)


def test_snapshot_change(mocker):
    # GIVEN: a dummy snapshot
    snapshot_name = "test_snapshot"
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
            snapshot_ops.VersionedSourcePackage(name=pkg_models.src_pkg_id("pkg1"), version="1.0"),
            snapshot_ops.VersionedSourcePackage(name=pkg_models.src_pkg_id("pkg2"), version="2.0"),
        ],
        pkg_index_path=pkg_index_path,
        parallel=2,
    )


def test_snapshot_reproduce(mocker):
    pass
