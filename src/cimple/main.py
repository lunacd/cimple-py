import pathlib
import typing

import typer

import cimple.cmd as cmd
import cimple.images as images
import cimple.pkg as pkg
import cimple.snapshot as snapshot

app = typer.Typer()
app.add_typer(cmd.snapshot.snapshot_app, name="snapshot")


@app.command(name="build-pkg")
def build_pkg(
    pkg_path: pathlib.Path,
    snapshot_name: typing.Annotated[
        str, typer.Option("--snapshot", help="Snapshot to build against")
    ],
    parallel: typing.Annotated[int, typer.Option(help="Number of parallel jobs")] = 1,
):
    snapshot_data = snapshot.ops.load_snapshot(snapshot_name)
    pkg.ops.build_pkg(pkg_path, parallel=parallel, snapshot_data=snapshot_data)


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
