import pathlib
import typing

import typer

import cimple.common as common
from cimple.models import pkg as pkg_models
from cimple.models import snapshot as snapshot_models
from cimple.snapshot import core as snapshot_core
from cimple.snapshot import ops as snapshot_ops

snapshot_app = typer.Typer()


@snapshot_app.command()
def change(
    origin_snapshot_name: typing.Annotated[str, typer.Option("--from")],
    add: typing.Annotated[list[str], typer.Option()],
    pkg_index: typing.Annotated[str, typer.Option()],
    parallel: typing.Annotated[int, typer.Option(help="Number of parallel jobs")] = 1,
):
    def parse_versioned_pkg(pkg_str: str) -> snapshot_ops.VersionedSourcePackage:
        segments = pkg_str.split("=")
        if len(segments) != 2:
            raise RuntimeError(
                f"{pkg_str} is not a valid package ID. Pass in <pkg name>=<pkg version>"
            )

        return snapshot_ops.VersionedSourcePackage(
            name=pkg_models.src_pkg_id(segments[0]), version=segments[1]
        )

    add_pkgs = [parse_versioned_pkg(pkg_str) for pkg_str in add] if len(add) > 0 else []

    origin_snapshot = snapshot_core.load_snapshot(origin_snapshot_name)

    # TODO: handle removal
    # TODO: handle version update

    snapshot_data = snapshot_ops.add(
        origin_snapshot=origin_snapshot,
        packages=add_pkgs,
        pkg_index_path=pathlib.Path(pkg_index),
        parallel=parallel,
    )
    snapshot_data.dump_snapshot()


@snapshot_app.command()
def reproduce(
    reproduce_snapshot_name: typing.Annotated[str, typer.Option],
    pkg_index: typing.Annotated[str, typer.Option()],
    parallel: typing.Annotated[int, typer.Option(help="Number of parallel jobs")],
):
    root_snapshot = snapshot_core.load_snapshot("root")
    snapshot_to_reproduce = snapshot_core.load_snapshot(reproduce_snapshot_name)

    pkgs_to_add = [
        snapshot_ops.VersionedSourcePackage(name=package_id, version=package_data.root.version)
        for package_id, package_data in snapshot_to_reproduce.pkg_map.items()
        if pkg_models.pkg_is_src(package_id)
        and snapshot_models.snapshot_pkg_is_src(package_data.root)
    ]

    result_snapshot = snapshot_ops.add(
        root_snapshot,
        pkgs_to_add,
        pkg_index_path=pathlib.Path(pkg_index),
        parallel=parallel,
    )

    different_pkg_id = result_snapshot.compare_pkgs_with(snapshot_to_reproduce)

    if different_pkg_id is None:
        common.logging.info(
            "All packages in snapshot %s are reproducible!", reproduce_snapshot_name
        )
        return

    common.logging.info(
        "%s in snapshot %s is not reproducible!", different_pkg_id, reproduce_snapshot_name
    )
    common.logging.info(
        "Dumping package data for %s obtained from reproduction...", different_pkg_id
    )
    package_data = result_snapshot.get_snapshot_pkg(different_pkg_id)
    assert package_data is not None
    common.logging.info("%s", package_data.model_dump_json(indent=2))
