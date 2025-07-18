import pathlib
import typing

import typer

import cimple.common as common
import cimple.pkg as pkg
import cimple.snapshot as snapshot

snapshot_app = typer.Typer()


@snapshot_app.command()
def change(
    origin_snapshot_name: typing.Annotated[str, typer.Option("--from")],
    add: typing.Annotated[list[str], typer.Option()],
    pkg_index: typing.Annotated[str, typer.Option()],
    parallel: typing.Annotated[int, typer.Option(help="Number of parallel jobs")],
):
    def parse_pkg_id(pkg_str: str) -> pkg.PkgId:
        segments = pkg_str.split("=")
        if len(segments) != 2:
            raise RuntimeError(
                f"{pkg_str} is not a valid package ID. Pass in <pkg name>=<pkg version>"
            )

        return pkg.PkgId(name=segments[0], version=segments[1])

    add_pkgs = [parse_pkg_id(pkg_str) for pkg_str in add] if len(add) > 0 else []

    origin_snapshot = snapshot.ops.load_snapshot(origin_snapshot_name)
    origin_snapshot.ancestor = origin_snapshot_name
    origin_snapshot.changes.add = add_pkgs

    # TODO: handle removal

    snapshot_data = snapshot.ops.add(
        origin_snapshot=origin_snapshot,
        packages=add_pkgs,
        pkg_index_path=pathlib.Path(pkg_index),
        parallel=parallel,
    )
    snapshot.ops.dump_snapshot(snapshot_data)


@snapshot_app.command()
def reproduce(
    reproduce_snapshot_name: typing.Annotated[str, typer.Option],
    pkg_index: typing.Annotated[str, typer.Option()],
    parallel: typing.Annotated[int, typer.Option(help="Number of parallel jobs")],
):
    root_snapshot = snapshot.ops.load_snapshot("root")
    snapshot_to_reproduce = snapshot.ops.load_snapshot(reproduce_snapshot_name)

    pkgs_to_add = [
        pkg.PkgId(name=package.name, version=package.version)
        for package in snapshot_to_reproduce.pkgs
    ]

    result_snapshot = snapshot.ops.add(
        root_snapshot,
        pkgs_to_add,
        pkg_index_path=pathlib.Path(pkg_index),
        parallel=parallel,
    )
    pkg_sha_values = {package.name: package.sha256 for package in snapshot_to_reproduce.pkgs}

    has_error = False

    for result_package in result_snapshot.pkgs:
        expected_sha = pkg_sha_values[result_package.name]
        if expected_sha != result_package.sha256:
            has_error = True
            common.logging.error(
                "%s is not reproducible, expecting %s but got %s.",
                result_package.name,
                expected_sha,
                result_package.sha256,
            )

    if not has_error:
        common.logging.info(
            "All packages in snapshot %s are reproducible!", reproduce_snapshot_name
        )
