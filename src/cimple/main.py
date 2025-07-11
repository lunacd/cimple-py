import pathlib
import typing

import typer

import cimple.common as common
import cimple.images as images
import cimple.pkg as pkg

app = typer.Typer()


@app.command(name="build-pkg")
def build_pkg():
    pkg.build_pkg()


@app.command()
def build():
    print("building")


@app.command()
def clean(target: str):
    if target == "all":
        common.image.clean_images()

    if target == "images":
        common.image.clean_images()
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
