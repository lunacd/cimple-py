import pathlib
import typing

import typer

import cimple.images as images
from cimple import cmd
from cimple.models import pkg as pkg_models
from cimple.pkg import ops as pkg_ops
from cimple.snapshot import core as snapshot_core

app = typer.Typer()
app.add_typer(cmd.snapshot.snapshot_app, name="snapshot")


@app.command(name="build-pkg")
def build_pkg(
    pkg_name: typing.Annotated[str, typer.Option("--pkg")],
    pkg_version: typing.Annotated[str, typer.Option("--version")],
    snapshot_name: typing.Annotated[
        str, typer.Option("--snapshot", help="Snapshot to build against")
    ],
    pkg_index_path: typing.Annotated[str, typer.Option()],
    parallel: typing.Annotated[int, typer.Option(help="Number of parallel jobs")] = 1,
):
    snapshot_map = snapshot_core.load_snapshot(snapshot_name)
    pkg_processor = pkg_ops.PkgOps()
    pkg_processor.build_pkg(
        pkg_models.src_pkg_id(pkg_name),
        pkg_version,
        pi_path=pathlib.Path(pkg_index_path),
        parallel=parallel,
        cimple_snapshot=snapshot_map,
    )


@app.command()
def build():
    print("building")


@app.command()
def clean(target: str):
    # TODO: support all of the added directories
    if target == "all":
        images.clean_images()

    if target == "images":
        images.clean_images()
    elif target != "all":
        print(f"Unknown target: {target}. Supported targets: images.")


@app.command()
def build_image(
    name: str,
    target_path: typing.Annotated[str, typer.Option()],
    msys_path: typing.Annotated[str | None, typer.Option()] = None,
):
    if name == "windows-bootstrap_msys-x86_64":
        assert msys_path is not None, "msys_path must be provided for windows-bootstrap-msys-x86_64"
        images.windows_bootstrap_msys_x86_64.make_image(
            pathlib.Path(msys_path), pathlib.Path(target_path)
        )


def main():
    app()
