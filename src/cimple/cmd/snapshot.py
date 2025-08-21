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
    root_snapshot_map = snapshot_core.load_snapshot("root")
    snapshot_to_reproduce = snapshot_core.load_snapshot(reproduce_snapshot_name)

    pkgs_to_add = [
        snapshot_ops.VersionedSourcePackage(name=package_id, version=package_data.root.version)
        for package_id, package_data in snapshot_to_reproduce.pkg_map.items()
        if pkg_models.pkg_is_src(package_id)
        and snapshot_models.snapshot_pkg_is_src(package_data.root)
    ]

    result_snapshot = snapshot_ops.add(
        root_snapshot_map,
        pkgs_to_add,
        pkg_index_path=pathlib.Path(pkg_index),
        parallel=parallel,
    )
    pkg_sha_values = {
        package_id: package_data.root.sha256
        for package_id, package_data in snapshot_to_reproduce.pkg_map.items()
        if pkg_models.pkg_is_bin(package_id)
        and snapshot_models.snapshot_pkg_is_bin(package_data.root)
    }

    has_error = False

    for result_package in result_snapshot.pkg_map.values():
        if not snapshot_models.snapshot_pkg_is_bin(result_package.root):
            continue
        expected_sha = pkg_sha_values[result_package.root.id]
        if expected_sha != result_package.root.sha256:
            has_error = True
            common.logging.error(
                "%s is not reproducible, expecting %s but got %s.",
                result_package.root.name,
                expected_sha,
                result_package.root.sha256,
            )

    if not has_error:
        common.logging.info(
            "All packages in snapshot %s are reproducible!", reproduce_snapshot_name
        )
