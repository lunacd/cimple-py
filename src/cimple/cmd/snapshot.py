import pathlib
import typing

import typer

import cimple.logging
import cimple.models.snapshot
from cimple.models import pkg as pkg_models
from cimple.snapshot import core as snapshot_core
from cimple.snapshot import ops as snapshot_ops

snapshot_app = typer.Typer()


@snapshot_app.command()
def change(
    origin_snapshot_name: typing.Annotated[str, typer.Option("--from")],
    add: typing.Annotated[list[str], typer.Option()],
    pkg_index: typing.Annotated[str, typer.Option()],
    parallel: typing.Annotated[int, typer.Option(help="Number of parallel jobs")] = 1,
    extra_paths: typing.Annotated[
        list[pathlib.Path] | None, typer.Option("--dangerously-add-extra-bin-path")
    ] = None,
):
    if extra_paths is None:
        extra_paths = []

    def parse_versioned_pkg(pkg_str: str) -> snapshot_ops.VersionedSourcePackage:
        segments = pkg_str.split("=")
        if len(segments) != 2:
            raise RuntimeError(
                f"{pkg_str} is not a valid package ID. Pass in <pkg name>=<pkg version>"
            )

        return snapshot_ops.VersionedSourcePackage(
            id=pkg_models.SrcPkgId(segments[0]), version=segments[1]
        )

    add_pkgs = [parse_versioned_pkg(pkg_str) for pkg_str in add] if len(add) > 0 else []

    snapshot = snapshot_core.load_snapshot(origin_snapshot_name)

    # TODO: handle removal
    # TODO: handle version update
    # TODO: add bootstrap support
    changes = cimple.models.snapshot.SnapshotChanges.model_construct(
        add=[
            cimple.models.snapshot.SnapshotChangeAdd.model_construct(
                name=pkg.id.name,
                version=pkg.version,
            )
            for pkg in add_pkgs
        ],
        remove=[],
        update=[],
    )

    snapshot_ops.process_changes(
        origin_snapshot=snapshot,
        pkg_changes=changes,
        bootstrap_changes=cimple.models.snapshot.SnapshotChanges.model_construct(
            add=[], remove=[], update=[]
        ),
        pkg_index_path=pathlib.Path(pkg_index),
        parallel=parallel,
        extra_paths=extra_paths,
    )
    snapshot.dump_snapshot()


@snapshot_app.command()
def reproduce(
    reproduce_snapshot_name: typing.Annotated[str, typer.Option],
    pkg_index: typing.Annotated[str, typer.Option()],
    parallel: typing.Annotated[int, typer.Option(help="Number of parallel jobs")],
):
    snapshot = snapshot_core.load_snapshot("root")
    snapshot_to_reproduce = snapshot_core.load_snapshot(reproduce_snapshot_name)

    bootstrap_pkgs_to_add = [
        snapshot_ops.VersionedSourcePackage(id=package_id, version=package_data.version)
        for package_id, package_data in snapshot_to_reproduce.bootstrap_src_pkg_map.items()
    ]
    bootstrap_changes = cimple.models.snapshot.SnapshotChanges.model_construct(
        add=[
            cimple.models.snapshot.SnapshotChangeAdd.model_construct(
                name=pkg.id.name,
                version=pkg.version,
            )
            for pkg in bootstrap_pkgs_to_add
        ],
        remove=[],
        update=[],
    )
    pkgs_to_add = [
        snapshot_ops.VersionedSourcePackage(id=package_id, version=package_data.version)
        for package_id, package_data in snapshot_to_reproduce.src_pkg_map.items()
    ]
    pkg_changes = cimple.models.snapshot.SnapshotChanges.model_construct(
        add=[
            cimple.models.snapshot.SnapshotChangeAdd.model_construct(
                name=pkg.id.name,
                version=pkg.version,
            )
            for pkg in pkgs_to_add
        ],
        remove=[],
        update=[],
    )

    snapshot_ops.process_changes(
        origin_snapshot=snapshot,
        pkg_changes=pkg_changes,
        bootstrap_changes=bootstrap_changes,
        pkg_index_path=pathlib.Path(pkg_index),
        parallel=parallel,
    )

    different_pkg_id = snapshot.compare_pkgs_with(snapshot_to_reproduce)

    if different_pkg_id is None:
        cimple.logging.info(
            "All packages in snapshot %s are reproducible!", reproduce_snapshot_name
        )
        return

    cimple.logging.info(
        "%s in snapshot %s is not reproducible!", different_pkg_id, reproduce_snapshot_name
    )
    cimple.logging.info(
        "Dumping package data for %s obtained from reproduction...", different_pkg_id
    )
    package_data = (
        snapshot.src_pkg_map[different_pkg_id]
        if different_pkg_id.type == "src"
        else snapshot.bin_pkg_map[different_pkg_id]
    )
    cimple.logging.info("%s", package_data.model_dump_json(indent=2))
